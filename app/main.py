from fastapi import FastAPI
from app.db.session import engine, Base
from app.api import scripts, campaigns, contacts, conversations, analytics

app = FastAPI(title="AI Sales Manager API", version="0.1.0")

app.include_router(scripts.router)
app.include_router(campaigns.router)
app.include_router(contacts.router)
app.include_router(conversations.router)
app.include_router(analytics.router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "ok"}
