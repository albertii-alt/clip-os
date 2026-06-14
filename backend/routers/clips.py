from fastapi import APIRouter, HTTPException
from database import supabase
from models.schemas import ClipUpdate

router = APIRouter()


@router.get("/{job_id}")
def get_clips_for_job(job_id: str):
    result = (
        supabase.table("clips")
        .select("*")
        .eq("job_id", job_id)
        .order("viral_score", desc=True)
        .execute()
    )
    return result.data


@router.patch("/{clip_id}")
def update_clip(clip_id: str, payload: ClipUpdate):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    result = supabase.table("clips").update(updates).eq("id", clip_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Clip not found")
    return result.data[0]