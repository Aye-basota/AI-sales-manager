import os
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.telegram_account import TelegramAccount
from app.schemas.telegram_account import (
    TelegramAccountCreate,
    TelegramAccountUpdate,
    TelegramAccountResponse,
)

router = APIRouter(prefix="/telegram-accounts", tags=["telegram-accounts"])


def _encrypt_session(session_string: str | None) -> str | None:
    if not session_string:
        return None
    key = os.getenv("SESSION_ENCRYPTION_KEY", "")
    if not key:
        try:
            from app.config import get_settings

            key = get_settings().session_encryption_key
        except Exception:
            key = ""
    if not key:
        return session_string
    try:
        from cryptography.fernet import Fernet

        if isinstance(key, str):
            key = key.encode()
        fernet = Fernet(key)
        return fernet.encrypt(session_string.encode()).decode()
    except Exception:
        return session_string


@router.get("", response_model=List[TelegramAccountResponse])
async def list_telegram_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TelegramAccount))
    return result.scalars().all()


@router.get("/{account_id}", response_model=TelegramAccountResponse)
async def get_telegram_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")
    return account


@router.post("", response_model=TelegramAccountResponse, status_code=201)
async def create_telegram_account(
    payload: TelegramAccountCreate, db: AsyncSession = Depends(get_db)
):
    data = payload.model_dump()
    data["session_string"] = _encrypt_session(data.get("session_string"))
    account = TelegramAccount(**data)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.put("/{account_id}", response_model=TelegramAccountResponse)
async def update_telegram_account(
    account_id: UUID, payload: TelegramAccountUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "session_string" in update_data and update_data["session_string"]:
        update_data["session_string"] = _encrypt_session(update_data["session_string"])
    for key, value in update_data.items():
        setattr(account, key, value)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
async def delete_telegram_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TelegramAccount).where(TelegramAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Telegram account not found")
    await db.delete(account)
    await db.commit()
    return None
