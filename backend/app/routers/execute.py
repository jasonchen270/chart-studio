from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.auth import User
from app.services.cache import get_csv_blob
from app.services.executor import run_user_code

router = APIRouter()


class ExecuteRequest(BaseModel):
    csv_hash: str
    code: str


class ExecuteResponse(BaseModel):
    ok: bool
    figure: dict | None = None
    error: str | None = None
    duration_ms: int


@router.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest, user: User) -> ExecuteResponse:
    csv_bytes = await get_csv_blob(req.csv_hash)
    if csv_bytes is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "csv not in cache, please re-upload")

    result = await run_user_code(req.code, csv_bytes)
    return ExecuteResponse(
        ok=result.ok,
        figure=result.figure,
        error=result.error,
        duration_ms=result.duration_ms,
    )
