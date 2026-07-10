"""Contact import helpers for CSV and Excel files."""

import io
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.schemas.contact import ContactCreate

_ALLOWED_COLUMNS = set(ContactCreate.model_fields.keys())
_STANDARD_COLUMNS = {
    "first_name",
    "last_name",
    "phone",
    "telegram_username",
    "company_name",
    "position",
    "city",
    "industry",
    "status",
}


def _process_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Validate and convert a DataFrame into a list of dicts suitable for Contact creation.

    Raises:
        ValueError: If the DataFrame contains unknown columns or is otherwise invalid.
    """
    if df.empty:
        return []

    # Normalise column names
    df.columns = [str(col).strip() for col in df.columns]

    # Support both telegram_id and telegram_user_id column names
    if "telegram_id" in df.columns:
        df = df.rename(columns={"telegram_id": "telegram_user_id"})

    file_columns = set(df.columns)

    if "telegram_user_id" not in file_columns:
        raise ValueError("Не найдена колонка telegram_user_id (или telegram_id)")

    unknown = file_columns - _ALLOWED_COLUMNS
    if unknown:
        raise ValueError(
            f"Invalid columns in file: {', '.join(sorted(unknown))}. "
            f"Allowed columns: {', '.join(sorted(_ALLOWED_COLUMNS))}"
        )

    # Keep only columns that map to the Contact model
    relevant_columns = list(file_columns & _ALLOWED_COLUMNS)
    df = df[relevant_columns]

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        record = {key: value for key, value in row.to_dict().items() if pd.notna(value)}
        if not record:
            continue

        # Coerce numeric/UUID fields so they match the database types.
        if "telegram_user_id" in record:
            try:
                record["telegram_user_id"] = int(record["telegram_user_id"])
            except (ValueError, TypeError):
                record.pop("telegram_user_id", None)

        if "icp_score" in record:
            try:
                record["icp_score"] = int(record["icp_score"])
            except (ValueError, TypeError):
                record.pop("icp_score", None)

        records.append(record)

    return records


def parse_csv(file_bytes: bytes) -> list[dict[str, Any]]:
    """Parse a CSV byte stream and return a list of contact dicts.

    Args:
        file_bytes: Raw bytes of the CSV file.

    Returns:
        A list of dictionaries that can be passed to ``Contact`` creation.

    Raises:
        ValueError: If the file cannot be parsed or contains invalid columns.
    """
    try:
        df = pd.read_csv(io.BytesIO(file_bytes), dtype=str)
    except Exception as exc:
        raise ValueError(f"Failed to parse CSV file: {exc}") from exc

    return _process_dataframe(df)


def parse_excel(file_bytes: bytes) -> list[dict[str, Any]]:
    """Parse an Excel byte stream and return a list of contact dicts.

    Args:
        file_bytes: Raw bytes of the Excel file.

    Returns:
        A list of dictionaries that can be passed to ``Contact`` creation.

    Raises:
        ValueError: If the file cannot be parsed or contains invalid columns.
    """
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    except Exception as exc:
        raise ValueError(f"Failed to parse Excel file: {exc}") from exc

    return _process_dataframe(df)


async def upsert_contacts(
    db: AsyncSession,
    records: list[dict[str, Any]],
    source: str = "csv_import",
) -> tuple[list[Contact], list[Contact]]:
    """Insert or update contacts, deduplicating by telegram_username and phone.

    Args:
        db: Active SQLAlchemy async session.
        records: List of contact dicts.
        source: The source tag (e.g. ``csv_import``, ``telegram_search``).

    Returns:
        Tuple of (created contacts, updated contacts).
    """
    created: list[Contact] = []
    updated: list[Contact] = []

    # Pre-load existing contacts by stable identifiers to avoid N+1 queries.
    telegram_user_ids = [
        int(r["telegram_user_id"]) for r in records if r.get("telegram_user_id")
    ]
    usernames = [
        r["telegram_username"].lower() for r in records if r.get("telegram_username")
    ]
    phones = [r["phone"] for r in records if r.get("phone")]

    existing_by_telegram_user_id: dict[int, Contact] = {}
    existing_by_username: dict[str, Contact] = {}
    existing_by_phone: dict[str, Contact] = {}

    if telegram_user_ids:
        result = await db.execute(
            select(Contact)
            .where(Contact.telegram_user_id.in_(telegram_user_ids))
            .order_by(
                Contact.updated_at.desc().nullslast(),
                Contact.created_at.desc().nullslast(),
            )
        )
        for contact in result.scalars().all():
            if contact.telegram_user_id and contact.telegram_user_id not in existing_by_telegram_user_id:
                existing_by_telegram_user_id[int(contact.telegram_user_id)] = contact

    if usernames:
        result = await db.execute(
            select(Contact)
            .where(Contact.telegram_username.in_(usernames))
            .order_by(
                Contact.updated_at.desc().nullslast(),
                Contact.created_at.desc().nullslast(),
            )
        )
        for contact in result.scalars().all():
            if contact.telegram_username:
                key = contact.telegram_username.lower()
                if key not in existing_by_username:
                    existing_by_username[key] = contact

    if phones:
        result = await db.execute(
            select(Contact)
            .where(Contact.phone.in_(phones))
            .order_by(
                Contact.updated_at.desc().nullslast(),
                Contact.created_at.desc().nullslast(),
            )
        )
        for contact in result.scalars().all():
            if contact.phone and contact.phone not in existing_by_phone:
                existing_by_phone[contact.phone] = contact

    for record in records:
        telegram_user_id = record.get("telegram_user_id")
        username = record.get("telegram_username")
        phone = record.get("phone")
        existing: Contact | None = None

        if telegram_user_id:
            existing = existing_by_telegram_user_id.get(int(telegram_user_id))
        if not existing and username:
            existing = existing_by_username.get(username.lower())
        if not existing and phone:
            existing = existing_by_phone.get(phone)

        if existing:
            # Update only empty fields (don't overwrite existing data with blanks)
            for key, value in record.items():
                if value and not getattr(existing, key, None):
                    setattr(existing, key, value)
            existing.last_source = source
            if "is_valid" in record:
                existing.is_valid = record["is_valid"]
            updated.append(existing)
        else:
            record["source"] = source
            record["last_source"] = source
            if "is_valid" not in record:
                record["is_valid"] = "unknown"
            contact = Contact(**record)
            db.add(contact)
            created.append(contact)
            if telegram_user_id:
                existing_by_telegram_user_id[int(telegram_user_id)] = contact
            if username:
                existing_by_username[username.lower()] = contact
            if phone:
                existing_by_phone[phone] = contact

    await db.commit()
    for contact in created:
        await db.refresh(contact)
    for contact in updated:
        await db.refresh(contact)

    return created, updated
