from workers.celery_app import celery_app
from database import supabase
from services import ingestion, transcription, analysis, video_processing
import traceback


def update_job_status(job_id: str, status: str, error: str = None):
    update = {"status": status}
    if error:
        update["error_message"] = error
    supabase.table("jobs").update(update).eq("id", job_id).execute()


@celery_app.task(bind=True, max_retries=1)
def run_pipeline(self, job_id: str):
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
        update_job_status(job_id, "transcribing")
        transcript = transcription.transcribe(video_path, job_id)

        # Step 3: Analyze
        update_job_status(job_id, "analyzing")
        moments = analysis.analyze(transcript, campaign)

        # Step 4: Render clips
        update_job_status(job_id, "rendering")
        video_processing.render_clips(video_path, moments, job_id)

        # Done
        update_job_status(job_id, "done")

    except Exception as e:
        update_job_status(job_id, "failed", error=traceback.format_exc())
        raise self.retry(exc=e, countdown=5)