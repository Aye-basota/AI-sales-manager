from __future__ import annotations

from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.campaign import Campaign
from app.models.funnel import Funnel
from app.schemas.funnel import (
    FunnelResponse,
    FunnelUploadRequest,
    FunnelPreviewRequest,
)
from app.services.funnel_parser import FunnelParseError, parse_funnel

router = APIRouter(prefix="/api/funnels", tags=["funnels"])


def _stages_to_response(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize stage dicts to match the response schema."""
    return [
        {
            "stage": s.get("stage", ""),
            "goal": s.get("goal", ""),
            "instructions": s.get("instructions", ""),
            "max_length": s.get("max_length", 400),
            "allow_call_to_action": s.get("allow_call_to_action", False),
        }
        for s in stages
    ]


@router.post("/preview", response_model=FunnelResponse)
async def preview_funnel(
    payload: FunnelPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Parse a funnel definition without persisting it."""
    try:
        stages = parse_funnel(payload.content, payload.format)
    except FunnelParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "id": UUID(int=0),  # preview has no real id
        "name": payload.name,
        "campaign_id": None,
        "stages": _stages_to_response(stages),
        "source_format": payload.format,
        "notes": None,
        "created_at": None,
    }


@router.post("/upload", response_model=FunnelResponse, status_code=status.HTTP_201_CREATED)
async def upload_funnel(
    payload: FunnelUploadRequest,
    db: AsyncSession = Depends(get_db),
):
    """Parse and persist a funnel definition."""
    try:
        stages = parse_funnel(payload.content, payload.format)
    except FunnelParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Validate campaign if provided
    if payload.campaign_id:
        campaign_result = await db.execute(
            select(Campaign).where(Campaign.id == payload.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Prevent overwriting an active funnel unless force=True
        existing_result = await db.execute(
            select(Funnel).where(Funnel.campaign_id == payload.campaign_id)
        )
        existing = existing_result.scalar_one_or_none()
        if existing and campaign.status == "running" and not payload.force:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign is running. Use force=true to overwrite the active funnel."
                ),
            )
        if existing:
            await db.delete(existing)

    funnel = Funnel(
        name=payload.name,
        campaign_id=payload.campaign_id,
        stages=stages,
        source_format=payload.format,
        notes=payload.notes,
    )
    db.add(funnel)
    await db.commit()
    await db.refresh(funnel)
    return funnel


@router.get("", response_model=list[FunnelResponse])
async def list_funnels(db: AsyncSession = Depends(get_db)):
    """List all persisted funnels."""
    result = await db.execute(select(Funnel))
    return result.scalars().all()


@router.get("/{funnel_id}", response_model=FunnelResponse)
async def get_funnel(funnel_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single funnel by id."""
    result = await db.execute(select(Funnel).where(Funnel.id == funnel_id))
    funnel = result.scalar_one_or_none()
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")
    return funnel
