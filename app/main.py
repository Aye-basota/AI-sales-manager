from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.session import engine, Base
from app.api import scripts, campaigns, contacts, conversations, analytics
from app.bots import start_bot, stop_bot
from app.db.redis import close_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await start_bot()
    yield
    await stop_bot()
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
