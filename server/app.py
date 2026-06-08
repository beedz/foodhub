"""FoodHUD remote backend — Phase 1 blob store.

Single-user, single-token auth. Holds the whole FoodHUD document and serves it
via GET /data + PUT /data. Clients (TUI now; bot/Android later) compute on top.
"""
from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import store

USER_ID = "me"  # single-user deployment

app = FastAPI(title="FoodHUD API", version="1.0")


def require_token(authorization: str | None = Header(default=None)) -> str:
    """Validate `Authorization: Bearer <token>` against env FOODHUB_TOKEN."""
    expected = os.environ.get("FOODHUB_TOKEN")
    if not expected:
        # Misconfigured server — refuse rather than run wide open.
        raise HTTPException(status_code=503, detail="Server token not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid token")
    return USER_ID


class DataResponse(BaseModel):
    doc: dict
    updated_at: str | None


class PutResponse(BaseModel):
    updated_at: str


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/data", response_model=DataResponse)
def get_data(user_id: str = Depends(require_token)) -> DataResponse:
    doc, updated_at = store.get_doc(user_id)
    return DataResponse(doc=doc, updated_at=updated_at)


@app.put("/data", response_model=PutResponse)
def put_data(doc: dict, user_id: str = Depends(require_token)) -> PutResponse:
    updated_at = store.put_doc(user_id, doc)
    return PutResponse(updated_at=updated_at)
