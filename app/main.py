import asyncio
import logging
import os
import signal
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api import (
    scripts,
    campaigns,
    contacts,
    conversations,
    analytics,
    health,
    telegram_accounts,
    funnels,
)
from app.bots import is_admin_bot_configured, start_bot, stop_bot
from app.bots.inbound_listener import start_inbound_listeners, stop_inbound_listeners
from app.db.redis import close_redis
from app.core.scheduler import scheduler
from app.logging_config import setup_logging

_level = os.getenv("LOG_LEVEL")
setup_logging(_level)

logger = logging.getLogger(__name__)


def _observe_background_task(task: asyncio.Task, name: str) -> asyncio.Task:
    """Attach logging to background startup tasks so failures are not silent."""

    def _log_result(done_task: asyncio.Task) -> None:
        if done_task.cancelled():
            logger.info("Background task %s cancelled", name)
            return
        try:
            exc = done_task.exception()
        except asyncio.CancelledError:
            logger.info("Background task %s cancelled", name)
            return
        if exc is not None:
            logger.error(
                "Background task %s failed",
                name,
                exc_info=(type(exc), exc, exc.__traceback__),
            )
        else:
            logger.info("Background task %s finished", name)

    task.add_done_callback(_log_result)
    return task


async def _supervise_admin_bot() -> None:
    if not is_admin_bot_configured():
        await start_bot()
        return

    while True:
        try:
            await start_bot()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "Admin bot polling crashed",
                exc_info=(type(exc), exc, exc.__traceback__),
            )
        logger.warning("Admin bot polling stopped; restarting in 5 seconds")
        await asyncio.sleep(5)


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

    bot_task = _observe_background_task(
        asyncio.create_task(_supervise_admin_bot()),
        "admin_bot",
    )

    inbound_task = _observe_background_task(
        asyncio.create_task(start_inbound_listeners()),
        "inbound_listeners",
    )

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


app = FastAPI(title="AI Sales Manager API", version="0.5.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return 400 Bad Request with descriptive error details for invalid input."""
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return a stable JSON fallback for unexpected API errors."""
    logger.error(
        "Unhandled API error for %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(scripts.router)
app.include_router(campaigns.router)
app.include_router(contacts.router)
app.include_router(conversations.router)
app.include_router(analytics.router)
app.include_router(health.router)
app.include_router(telegram_accounts.router)
app.include_router(funnels.router)

# Serve the customer-facing landing site at the root URL
app.mount("/", StaticFiles(directory="site", html=True), name="site")
