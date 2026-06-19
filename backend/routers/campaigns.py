from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from database import supabase
from models.schemas import CampaignCreate, CampaignUpdate

router = APIRouter()


class CampaignPatch(BaseModel):
    name: Optional[str] = None
    creator_handle: Optional[str] = None
    platform: Optional[str] = None
    payout_per_1k: Optional[float] = None
    min_clip_length: Optional[int] = None
    max_clip_length: Optional[int] = None
    required_hashtags: Optional[List[str]] = None
    required_tags: Optional[List[str]] = None
    forbidden_topics: Optional[List[str]] = None
    style_notes: Optional[str] = None
    layout_style: Optional[str] = None
    boxed_background_color: Optional[str] = None


@router.get("/")
def list_campaigns():
    result = supabase.table("campaigns").select("*").order("created_at", desc=True).execute()
    return result.data


@router.post("/", status_code=201)
def create_campaign(payload: CampaignCreate):
    result = supabase.table("campaigns").insert(payload.model_dump()).execute()
    return result.data[0]


@router.put("/{campaign_id}")
def update_campaign(campaign_id: str, payload: CampaignUpdate):
    result = supabase.table("campaigns").update(payload.model_dump()).eq("id", campaign_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result.data[0]


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: str):
    supabase.table("campaigns").delete().eq("id", campaign_id).execute()


@router.patch("/{campaign_id}")
def patch_campaign(campaign_id: str, payload: CampaignPatch):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    result = supabase.table("campaigns").update(updates).eq("id", campaign_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result.data[0]