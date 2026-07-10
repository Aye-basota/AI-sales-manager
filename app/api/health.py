from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bots import is_admin_bot_configured, is_admin_bot_running
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
    admin_bot_ok = True
    if is_admin_bot_configured():
        admin_bot_ok = is_admin_bot_running()

    return {
        "status": "ok" if (db_ok and scheduler_ok and admin_bot_ok) else "degraded",
        "scheduler": scheduler_ok,
        "db": db_ok,
        "admin_bot": admin_bot_ok,
    }
