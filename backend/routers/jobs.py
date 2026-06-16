from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from database import supabase
from workers.pipeline import run_pipeline
import uuid

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
    file: Optional[UploadFile] = File(None)
):
    job_id = str(uuid.uuid4())

    job_data = {
        "id": job_id,
        "source_type": source_type,
        "source_url": source_url,
        "campaign_id": campaign_id,
        "status": "queued"
    }

    if file:
        import os
        from config import settings
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

    run_pipeline.delay(job_id)

    return {"job_id": job_id, "status": "queued"}