import io
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.services.contact_import import parse_csv, parse_excel

router = APIRouter(prefix="/contacts", tags=["contacts"])


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

    created = []
    for record in records:
        contact = Contact(**record)
        db.add(contact)
        created.append(contact)
    await db.commit()
    for contact in created:
        await db.refresh(contact)
    return created
