from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.scheduler import scheduler

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    scheduler_ok = scheduler.is_running()

    return {
        "status": "ok" if (db_ok and scheduler_ok) else "degraded",
        "scheduler": scheduler_ok,
        "db": db_ok,
    }
