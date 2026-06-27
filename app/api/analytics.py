from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.contact import Contact
from app.models.campaign import Campaign
from app.models.conversation import Message

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    total_contacts_result = await db.execute(select(func.count()).select_from(Contact))
    total_contacts = total_contacts_result.scalar() or 0

    campaigns_by_status = {}
    campaigns_result = await db.execute(
        select(Campaign.status, func.count()).group_by(Campaign.status)
    )
    for status, count in campaigns_result.all():
        campaigns_by_status[status] = count

    reply_rate_result = await db.execute(
        select(
            func.coalesce(func.sum(Campaign.replied_count), 0),
            func.coalesce(func.sum(Campaign.total_contacts), 0),
        )
    )
    replied, total = reply_rate_result.one()
    reply_rate = round((replied / total) * 100, 2) if total else 0.0

    qualified_result = await db.execute(select(func.sum(Campaign.qualified_count)))
    qualified_count = qualified_result.scalar() or 0

    meetings_result = await db.execute(select(func.sum(Campaign.meeting_booked_count)))
    meeting_booked_count = meetings_result.scalar() or 0

    # Message-level metrics
    outbound_result = await db.execute(
        select(func.count()).select_from(Message).where(Message.direction == "outbound")
    )
    outbound_count = outbound_result.scalar() or 0

    inbound_result = await db.execute(
        select(func.count()).select_from(Message).where(Message.direction == "inbound")
    )
    inbound_count = inbound_result.scalar() or 0

    rejected_result = await db.execute(
        select(func.count())
        .select_from(Message)
        .where(Message.direction == "outbound")
        .where(Message.llm_model == "fallback")
    )
    rejected_count = rejected_result.scalar() or 0

    avg_length_result = await db.execute(
        select(func.coalesce(func.avg(func.length(Message.content)), 0))
        .select_from(Message)
        .where(Message.direction == "outbound")
    )
    avg_message_length = round(avg_length_result.scalar() or 0, 1)

    return {
        "total_contacts": total_contacts,
        "campaigns_by_status": campaigns_by_status,
        "reply_rate": reply_rate,
        "qualified_count": qualified_count,
        "meeting_booked_count": meeting_booked_count,
        "outbound_messages": outbound_count,
        "inbound_messages": inbound_count,
        "guardrails_rejected": rejected_count,
        "avg_message_length": avg_message_length,
    }
