from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import require_admin

router = APIRouter()


@router.get("/me", dependencies=[Depends(require_admin)])
def admin_me() -> dict:
    return {"role": "admin", "ok": True}
