import io
from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.services.contact_import import parse_csv, parse_excel, upsert_contacts
from app.services.lead_discovery import LeadCriteria, DiscoveredContact, discover_leads, enrich_contact
from app.services.lead_validation import validate_and_enrich

router = APIRouter(prefix="/contacts", tags=["contacts"])


class DiscoverRequest(BaseModel):
    query: str
    source: str = "telegram_search"
    limit: int = 20
    criteria: dict[str, Any] = {}


class DiscoverConfirmRequest(BaseModel):
    contacts: List[dict[str, Any]]


@router.get("", response_model=List[ContactResponse])
async def list_contacts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact))
    return result.scalars().all()


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("", response_model=ContactResponse, status_code=201)
async def create_contact(payload: ContactCreate, db: AsyncSession = Depends(get_db)):
    contact = Contact(**payload.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(contact_id: UUID, payload: ContactUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete(contact)
    await db.commit()
    return None


@router.post("/import", response_model=List[ContactResponse], status_code=201)
async def import_contacts(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    contents = await file.read()
    try:
        if file.filename.endswith(".csv"):
            records = parse_csv(contents)
        elif file.filename.endswith((".xlsx", ".xls")):
            records = parse_excel(contents)
        else:
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    created, updated = await upsert_contacts(db, records, source="csv_import")
    return created + updated


@router.post("/discover", response_model=List[dict[str, Any]])
async def discover_contacts(payload: DiscoverRequest):
    """Preview discovered contacts without saving them."""
    criteria = LeadCriteria(
        query=payload.query,
        limit=payload.limit,
        keywords=payload.criteria.get("keywords", []),
        job_title=payload.criteria.get("job_title", ""),
        company=payload.criteria.get("company", ""),
    )
    discovered = await discover_leads(criteria, source=payload.source)

    # Enrich and validate in background (best effort)
    usernames = [d.telegram_username for d in discovered if d.telegram_username]
    valid_map = {}
    if usernames:
        try:
            valid_map = await validate_and_enrich(usernames)
        except Exception:
            pass

    results = []
    for d in discovered:
        entry = {
            "telegram_username": d.telegram_username,
            "telegram_user_id": d.telegram_user_id,
            "first_name": d.first_name,
            "last_name": d.last_name,
            "company_name": d.company_name,
            "position": d.position,
            "city": d.city,
            "industry": d.industry,
            "bio": d.bio,
            "source": d.source,
            "is_valid": d.telegram_username in valid_map,
        }
        if d.telegram_username in valid_map:
            info = valid_map[d.telegram_username]
            entry["telegram_user_id"] = info.get("user_id")
            entry["first_name"] = entry["first_name"] or info.get("first_name")
            entry["last_name"] = entry["last_name"] or info.get("last_name")
        results.append(entry)

    return results


@router.post("/discover/confirm", response_model=List[ContactResponse], status_code=201)
async def confirm_discovered_contacts(payload: DiscoverConfirmRequest, db: AsyncSession = Depends(get_db)):
    """Save discovered contacts to the database with deduplication."""
    records = []
    for item in payload.contacts:
        record = {k: v for k, v in item.items() if k in ContactCreate.model_fields}
        records.append(record)

    created, updated = await upsert_contacts(db, records, source="discover")
    return created + updated
