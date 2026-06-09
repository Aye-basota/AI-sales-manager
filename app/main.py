import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.db.session import engine, Base, AsyncSessionLocal
from app.api import scripts, campaigns, contacts, conversations, analytics
from app.bots import start_bot, stop_bot
from app.bots.inbound_listener import start_inbound_listeners, stop_inbound_listeners
from app.db.redis import close_redis
from app.core.scheduler import CampaignScheduler

scheduler = CampaignScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scheduler.start()

    bot_task = asyncio.create_task(start_bot())

    async with AsyncSessionLocal() as db:
        inbound_task = asyncio.create_task(start_inbound_listeners(db))

    yield

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

    scheduler.shutdown()
    await stop_bot()
    await stop_inbound_listeners()
    await close_redis()


app = FastAPI(title="AI Sales Manager API", version="0.1.0", lifespan=lifespan)

app.include_router(scripts.router)
app.include_router(campaigns.router)
app.include_router(contacts.router)
app.include_router(conversations.router)
app.include_router(analytics.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
