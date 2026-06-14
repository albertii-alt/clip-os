from fastapi import APIRouter, HTTPException
from database import supabase
from models.schemas import CampaignCreate, CampaignUpdate

router = APIRouter()


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