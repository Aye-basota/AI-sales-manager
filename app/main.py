import asyncio
import logging
import signal
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.db.session import engine, Base, AsyncSessionLocal
from app.api import scripts, campaigns, contacts, conversations, analytics, health
from app.bots import start_bot, stop_bot
from app.bots.inbound_listener import start_inbound_listeners, stop_inbound_listeners
from app.db.redis import close_redis
from app.core.scheduler import scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register signal handlers
    def _signal_handler(signum):
        logger.info("Received signal %s, initiating graceful shutdown...", signum)

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: _signal_handler(s))
    except (NotImplementedError, ValueError):
        # Windows fallback – add_signal_handler may not support all signals
        signal.signal(signal.SIGTERM, lambda s, f: _signal_handler(s))
        signal.signal(signal.SIGINT, lambda s, f: _signal_handler(s))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scheduler.start()

    bot_task = asyncio.create_task(start_bot())

    async with AsyncSessionLocal() as db:
        inbound_task = asyncio.create_task(start_inbound_listeners(db))

    yield

    # Graceful shutdown sequence
    await stop_inbound_listeners()
    scheduler.shutdown(wait=True)
    await stop_bot()
    await close_redis()

    inbound_task.cancel()
    try:
        await inbound_task
    except asyncio.CancelledError:
        pass

    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="AI Sales Manager API", version="0.1.0", lifespan=lifespan)

app.include_router(scripts.router)
app.include_router(campaigns.router)
app.include_router(contacts.router)
app.include_router(conversations.router)
app.include_router(analytics.router)
app.include_router(health.router)
