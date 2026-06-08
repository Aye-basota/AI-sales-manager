"""Contact import helpers for CSV and Excel files."""

import io
from typing import Any

import pandas as pd

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
    file_columns = set(df.columns)

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
        record = {
            key: value
            for key, value in row.to_dict().items()
            if pd.notna(value)
        }
        if record:
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
