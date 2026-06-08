from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.contact import Contact
from app.models.campaign import Campaign
from app.models.conversation import Conversation

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    total_contacts_result = await db.execute(select(func.count()).select_from(Contact))
    total_contacts = total_contacts_result.scalar() or 0

    campaigns_by_status = {}
    campaigns_result = await db.execute(select(Campaign.status, func.count()).group_by(Campaign.status))
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

    return {
        "total_contacts": total_contacts,
        "campaigns_by_status": campaigns_by_status,
        "reply_rate": reply_rate,
        "qualified_count": qualified_count,
        "meeting_booked_count": meeting_booked_count,
    }
