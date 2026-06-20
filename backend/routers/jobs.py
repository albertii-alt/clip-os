from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from database import supabase
from workers.pipeline import run_pipeline
from workers.celery_app import celery_app
from config import settings
import uuid
import shutil
import os

router = APIRouter()


@router.get("/")
def list_jobs():
    result = supabase.table("jobs").select("*").order("created_at", desc=True).execute()
    return result.data


@router.get("/{job_id}")
def get_job(job_id: str):
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return result.data


@router.post("/", status_code=201)
async def create_job(
    source_type: str = Form(...),
    source_url: Optional[str] = Form(None),
    campaign_id: Optional[str] = Form(None),
    layout_style: str = Form('full_bleed'),
    boxed_background_color: str = Form('black'),
    font_choice: str = Form('arial'),
    file: Optional[UploadFile] = File(None)
):
    job_id = str(uuid.uuid4())

    job_data = {
        "id": job_id,
        "source_type": source_type,
        "source_url": source_url,
        "campaign_id": campaign_id,
        "layout_style": layout_style,
        "boxed_background_color": boxed_background_color,
        "font_choice": font_choice,
        "status": "queued"
    }

    if file:
        tmp_dir = f"{settings.tmp_dir}/{job_id}"
        os.makedirs(tmp_dir, exist_ok=True)
        local_path = f"{tmp_dir}/input.mp4"

        file_bytes = await file.read()
        with open(local_path, "wb") as f_out:
            f_out.write(file_bytes)

        job_data["storage_path"] = local_path
        job_data["original_filename"] = file.filename

    elif source_type == "local_path" and source_url:
        job_data["storage_path"] = source_url

    supabase.table("jobs").insert(job_data).execute()

    task = run_pipeline.delay(job_id)
    supabase.table("jobs").update({"celery_task_id": task.id}).eq("id", job_id).execute()

    return {"job_id": job_id, "status": "queued"}


@router.post("/{job_id}/retry")
def retry_job(job_id: str):
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    job = result.data

    if job["status"] != "failed":
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")

    supabase.table("jobs").update({
        "status": "queued",
        "error_message": None,
        "cancelled": False,
    }).eq("id", job_id).execute()

    task = run_pipeline.delay(job_id)
    supabase.table("jobs").update({"celery_task_id": task.id}).eq("id", job_id).execute()

    return {"status": "queued", "job_id": job_id}


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str):
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    job = result.data

    celery_task_id = job.get("celery_task_id")
    if celery_task_id:
        celery_app.control.revoke(celery_task_id, terminate=True, signal="SIGTERM")

    supabase.table("jobs").update({"status": "cancelled", "cancelled": True}).eq("id", job_id).execute()

    tmp_dir = f"{settings.tmp_dir}/{job_id}"
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return {"status": "cancelled"}


@router.delete("/{job_id}")
def delete_job(job_id: str):
    result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete permanent local clips folder
    clip_dir = os.path.join(settings.clips_dir, job_id)
    shutil.rmtree(clip_dir, ignore_errors=True)

    # Delete job row (clips cascade via FK)
    supabase.table("jobs").delete().eq("id", job_id).execute()

    return {"status": "deleted"}