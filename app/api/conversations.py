from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationResponse,
    ConversationUpdateStatus,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation))
    return result.scalars().all()


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.sent_at)
    )
    return result.scalars().all()


@router.put("/{conversation_id}/status", response_model=ConversationResponse)
async def update_conversation_status(
    conversation_id: UUID,
    payload: ConversationUpdateStatus,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation.operator_status = payload.operator_status
    if payload.operator_notes is not None:
        conversation.operator_notes = payload.operator_notes
    # Any operator-driven status change counts as human escalation for automation tracking.
    if payload.operator_status:
        conversation.was_escalated = True
    await db.commit()
    await db.refresh(conversation)
    return conversation
