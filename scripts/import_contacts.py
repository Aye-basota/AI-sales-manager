# CLI import for contacts from CSV/Excel.
import argparse
import asyncio
import sys
from pathlib import Path

from app.services.contact_import import parse_csv, parse_excel
from app.db.session import AsyncSessionLocal
from app.models.contact import Contact


async def import_file(file_path: str) -> None:
    path = Path(file_path)
    data = path.read_bytes()

    if path.suffix == ".csv":
        records = parse_csv(data)
    elif path.suffix in (".xlsx", ".xls"):
        records = parse_excel(data)
    else:
        print("Unsupported file format. Use .csv or .xlsx")
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        for record in records:
            contact = Contact(**record)
            session.add(contact)
        await session.commit()

    print(f"Imported {len(records)} contacts.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import contacts from CSV or Excel")
    parser.add_argument("file", help="Path to CSV or Excel file")
    args = parser.parse_args()
    asyncio.run(import_file(args.file))


if __name__ == "__main__":
    main()
