from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.script import Script
from app.schemas.script import ScriptCreate, ScriptUpdate, ScriptResponse

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.get("", response_model=List[ScriptResponse])
async def list_scripts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Script))
    return result.scalars().all()


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.post("", response_model=ScriptResponse, status_code=201)
async def create_script(payload: ScriptCreate, db: AsyncSession = Depends(get_db)):
    script = Script(**payload.model_dump())
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return script


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: UUID, payload: ScriptUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(script, key, value)
    await db.commit()
    await db.refresh(script)
    return script


@router.delete("/{script_id}", status_code=204)
async def delete_script(script_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    await db.delete(script)
    await db.commit()
    return None
