import asyncio
import logging
import signal
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.db.session import engine, Base, AsyncSessionLocal
from app.api import scripts, campaigns, contacts, conversations, analytics, health, telegram_accounts
from app.bots import start_bot, stop_bot
from app.bots.inbound_listener import start_inbound_listeners, stop_inbound_listeners
from app.db.redis import close_redis
from app.core.scheduler import scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register signal handlers only when running in the main interpreter thread.
    # Tests and some deployment environments run the app in a background thread,
    # where signal handling is not available.
    if threading.current_thread() is threading.main_thread():
        def _signal_handler(signum):
            logger.info("Received signal %s, initiating graceful shutdown...", signum)

        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda s=sig: _signal_handler(s))
        except (NotImplementedError, ValueError, RuntimeError):
            # Windows fallback – add_signal_handler may not support all signals
            signal.signal(signal.SIGTERM, lambda s, f: _signal_handler(s))
            signal.signal(signal.SIGINT, lambda s, f: _signal_handler(s))

    scheduler.start()

    bot_task = asyncio.create_task(start_bot())

    inbound_task = asyncio.create_task(start_inbound_listeners())

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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return 400 Bad Request with descriptive error details for invalid input."""
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request", "errors": exc.errors()},
    )


app.include_router(scripts.router)
app.include_router(campaigns.router)
app.include_router(contacts.router)
app.include_router(conversations.router)
app.include_router(analytics.router)
app.include_router(health.router)
app.include_router(telegram_accounts.router)

# Serve the customer-facing landing site at the root URL
app.mount("/", StaticFiles(directory="site", html=True), name="site")
