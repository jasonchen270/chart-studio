from io import BytesIO

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.services.auth import User
from app.services.cache import hash_csv, put_csv_blob, put_dataframe

router = APIRouter()

_MAX_BYTES = 25 * 1024 * 1024  # 25 MB, comfortably above what fits in a single Plotly figure


@router.post("/upload")
async def upload_csv(user: User, file: UploadFile = File(...)) -> dict:
    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "csv exceeds 25MB")

    try:
        df = pd.read_csv(BytesIO(content))
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"could not parse csv: {exc}") from exc

    csv_hash = hash_csv(content)
    await put_csv_blob(csv_hash, content)
    await put_dataframe(csv_hash, df)

    return {
        "csv_hash": csv_hash,
        "rows": int(df.shape[0]),
        "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
    }
