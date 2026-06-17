from workers.celery_app import celery_app
from database import supabase
from services import ingestion, transcription, analysis, video_processing
from config import settings
import traceback
import shutil
import json
import os


class JobCancelledError(Exception):
    pass


def update_job_status(job_id: str, status: str, error: str = None):
    update = {"status": status}
    if error:
        update["error_message"] = error
    supabase.table("jobs").update(update).eq("id", job_id).execute()


def check_cancelled(job_id: str):
    result = supabase.table("jobs").select("cancelled").eq("id", job_id).single().execute()
    if result.data and result.data.get("cancelled"):
        raise JobCancelledError(f"Job {job_id} was cancelled")


@celery_app.task(bind=True)
def run_pipeline(self, job_id: str):
    tmp_dir = os.path.join(settings.tmp_dir, job_id)

    def cleanup(full: bool = True):
        if full:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            # Partial cleanup — keep input.mp4, transcript.json, moments.json
            # Remove only disposable intermediates: audio, chunks, clips subfolder
            keep = {"input.mp4", "transcript.json", "moments.json"}
            if os.path.isdir(tmp_dir):
                for entry in os.listdir(tmp_dir):
                    entry_path = os.path.join(tmp_dir, entry)
                    if entry in keep:
                        continue
                    if os.path.isdir(entry_path):
                        shutil.rmtree(entry_path, ignore_errors=True)
                    else:
                        try:
                            os.remove(entry_path)
                        except OSError:
                            pass

    try:
        # Fetch job
        result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
        job = result.data

        # Fetch campaign if attached
        campaign = None
        if job.get("campaign_id"):
            camp_result = supabase.table("campaigns").select("*").eq("id", job["campaign_id"]).single().execute()
            campaign = camp_result.data

        # Step 1: Ingest
        update_job_status(job_id, "downloading")
        video_path = ingestion.ingest(job, job_id)

        # Step 2: Transcribe
        check_cancelled(job_id)
        update_job_status(job_id, "transcribing")
        transcript = transcription.transcribe(video_path, job_id)

        # Step 3: Analyze — reuse cached moments.json if present
        check_cancelled(job_id)
        moments_path = os.path.join(tmp_dir, "moments.json")
        if os.path.exists(moments_path):
            print("[INFO] Reusing existing analysis results, skipping re-analysis")
            with open(moments_path) as f:
                moments = json.load(f)
        else:
            update_job_status(job_id, "analyzing")
            moments = analysis.analyze(transcript, campaign)
            with open(moments_path, "w") as f:
                json.dump(moments, f)

        # Step 4: Render — skip if clips already exist in DB
        check_cancelled(job_id)
        existing_clips = supabase.table("clips").select("id").eq("job_id", job_id).execute()
        if existing_clips.data:
            print("[INFO] Clips already rendered for this job, skipping re-render")
        else:
            update_job_status(job_id, "rendering")
            video_processing.render_clips(video_path, moments, job_id, campaign=campaign)

        # Terminal: success
        update_job_status(job_id, "done")
        cleanup(full=True)

    except JobCancelledError:
        # Terminal: cancelled
        update_job_status(job_id, "cancelled")
        cleanup(full=True)
    except Exception as e:
        # Terminal: failed — partial cleanup to preserve reusable artifacts
        update_job_status(job_id, "failed", error=traceback.format_exc())
        cleanup(full=False)