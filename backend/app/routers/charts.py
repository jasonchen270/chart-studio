"""Persist saved charts. The Supabase row-level security policy (see
supabase/migrations) is what actually enforces ownership; this handler
just passes the auth'd user_id through. Defense in depth: even if a router
forgot to filter, RLS would deny the read.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from supabase import Client, create_client

from app.config import get_settings
from app.services.auth import User

router = APIRouter()


def _supabase() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)


class ChartCreate(BaseModel):
    title: str
    prompt: str
    code: str
    csv_hash: str
    figure: dict


class Chart(ChartCreate):
    id: str
    owner_id: str
    created_at: str


@router.post("/charts", response_model=Chart, status_code=status.HTTP_201_CREATED)
async def create_chart(payload: ChartCreate, user: User) -> Chart:
    row = {**payload.model_dump(), "owner_id": user.id}
    res = _supabase().table("charts").insert(row).execute()
    if not res.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "insert returned no row")
    return Chart(**res.data[0])


@router.get("/charts", response_model=list[Chart])
async def list_charts(user: User) -> list[Chart]:
    res = (
        _supabase()
        .table("charts")
        .select("*")
        .eq("owner_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return [Chart(**row) for row in res.data]


@router.delete("/charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart(chart_id: str, user: User) -> None:
    _supabase().table("charts").delete().eq("id", chart_id).eq("owner_id", user.id).execute()
