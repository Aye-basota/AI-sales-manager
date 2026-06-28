from datetime import datetime, timezone
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.campaign import Campaign, CampaignContact
from app.models.contact import Contact
from app.schemas.campaign import (
    CampaignAddContacts,
    CampaignContactListItem,
    CampaignContactResponse,
    CampaignCreate,
    CampaignUpdateStatus,
    CampaignResponse,
)
from app.core.scheduler import process_campaigns

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign))
    return result.scalars().all()


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(**payload.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.put("/{campaign_id}/status", response_model=CampaignResponse)
async def update_campaign_status(
    campaign_id: UUID, payload: CampaignUpdateStatus, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = payload.status
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.delete(campaign)
    await db.commit()
    return None


@router.post(
    "/{campaign_id}/contacts",
    response_model=List[CampaignContactResponse],
    status_code=201,
)
async def add_contacts_to_campaign(
    campaign_id: UUID,
    payload: CampaignAddContacts,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    created = []
    for contact_id in payload.contact_ids:
        cc = CampaignContact(
            campaign_id=campaign_id,
            contact_id=contact_id,
            status="pending",
            message_count=0,
        )
        db.add(cc)
        created.append(cc)

    campaign.total_contacts += len(payload.contact_ids)
    await db.commit()
    for cc in created:
        await db.refresh(cc)
    return created


@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status != "draft":
        raise HTTPException(
            status_code=400, detail="Campaign can only be started from draft status"
        )
    campaign.status = "running"
    campaign.started_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(campaign)

    # Immediate campaign check (best-effort)
    try:
        await process_campaigns(db)
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Immediate process_campaigns failed after campaign start")

    return campaign


@router.post("/{campaign_id}/stop", response_model=CampaignResponse)
async def stop_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status != "running":
        raise HTTPException(
            status_code=400, detail="Campaign can only be stopped from running status"
        )
    campaign.status = "paused"
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}/contacts", response_model=List[CampaignContactListItem])
async def list_campaign_contacts(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await db.execute(
        select(Contact, CampaignContact)
        .join(CampaignContact, Contact.id == CampaignContact.contact_id)
        .where(CampaignContact.campaign_id == campaign_id)
    )
    rows = result.all()
    return [
        CampaignContactListItem(
            contact_id=row[0].id,
            first_name=row[0].first_name,
            last_name=row[0].last_name,
            company_name=row[0].company_name,
            position=row[0].position,
            phone=row[0].phone,
            telegram_username=row[0].telegram_username,
            city=row[0].city,
            industry=row[0].industry,
            source=row[0].source,
            icp_score=row[0].icp_score,
            contact_status=row[0].status,
            created_at=row[0].created_at,
            updated_at=row[0].updated_at,
            status=row[1].status,
            initial_sent_at=row[1].initial_sent_at,
            follow_up_sent_at=row[1].follow_up_sent_at,
            reply_received_at=row[1].reply_received_at,
            last_message_at=row[1].last_message_at,
            message_count=row[1].message_count,
        )
        for row in rows
    ]


@router.delete("/{campaign_id}/contacts/{contact_id}", status_code=204)
async def remove_contact_from_campaign(
    campaign_id: UUID,
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await db.execute(
        select(CampaignContact)
        .where(CampaignContact.campaign_id == campaign_id)
        .where(CampaignContact.contact_id == contact_id)
    )
    campaign_contact = result.scalar_one_or_none()
    if not campaign_contact:
        raise HTTPException(status_code=404, detail="Contact not found in campaign")

    await db.delete(campaign_contact)
    campaign.total_contacts = max((campaign.total_contacts or 0) - 1, 0)
    await db.commit()
    return None
