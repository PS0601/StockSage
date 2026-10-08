# SPDX-License-Identifier: MIT
"""FastAPI application for StockSage UI."""

import asyncio
import html
import json
import logging
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.app.mock_stream import stream_mock_logs
from src.app.utils.formatters import format_log_entry
from src.core.config.config import APP_MODE, DEV_STREAM_MODE, OUTPUT_DIR_PATH
from src.core.config.enums import (
    STAGE_REGISTRY,
    ProcessingStage,
    StatusType,
    get_total_pipeline_steps,
)
from src.core.processing import StockProcessor

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="StockSage",
    description=(
        "Local-first, multi-agent stock analysis. "
        "Enter a ticker symbol to get a full investment report streamed live to your browser."
    ),
    version="0.1.0",
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    contact={"url": "https://github.com/kanishk-varshney/StockSage/issues"},
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
logger = logging.getLogger(__name__)

# Mount static files
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add standard security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page."""
    stream_mode = DEV_STREAM_MODE if APP_MODE == "dev" else "live"
    runtime_config = {
        "appMode": APP_MODE,
        "streamMode": stream_mode,
        "totalPipelineSteps": get_total_pipeline_steps(),
        "stageLabels": {k: s["display_name"] for k, s in STAGE_REGISTRY.items()},
        "substageLabels": {
            sub_id: sub_name
            for s in STAGE_REGISTRY.values()
            for sub_id, sub_name in s["substages"].items()
        },
    }
    cache_bust = int(time.time()) if APP_MODE == "dev" else ""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"runtime_config": runtime_config, "v": cache_bust},
    )


SSE_RETRY_MS = 3000
UI_STREAM_CACHE_FILE = ".ui_stream_cache.json"


def _sse_data(html: str, event: str | None = None) -> str:
    """Format an HTML string as a valid SSE message, handling newlines."""
    flat = html.replace("\n", "").replace("\r", "")
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {flat}\n\n"


def _symbol_cache_file(symbol: str) -> Path:
    return OUTPUT_DIR_PATH / symbol.upper() / UI_STREAM_CACHE_FILE


def _public_error_message(symbol: str, error: Exception | None = None) -> str:
    """Return a sanitized user-facing error and log full details server-side."""
    ref = uuid4().hex[:8]
    if error is not None:
        logger.exception("Stream failure for %s (ref=%s)", symbol.upper(), ref, exc_info=error)
    return f"Analysis failed. Please retry. Reference: {ref}"


def _load_stream_cache(symbol: str) -> list[str]:
    cache_file = _symbol_cache_file(symbol)
    if not cache_file.exists():
        return []
    try:
        payload = json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError, ValueError):
        return []
    messages = payload.get("messages", [])
    return [m for m in messages if isinstance(m, str)]


def _save_stream_cache(symbol: str, messages: list[str]) -> None:
    if not messages:
        return
    cache_file = _symbol_cache_file(symbol)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"symbol": symbol.upper(), "messages": messages}
    try:
        cache_file.write_text(json.dumps(payload, ensure_ascii=True))
    except OSError:
        pass


async def stream_logs(symbol: str):
    """Stream log entries as Server-Sent Events."""
    yield f"retry: {SSE_RETRY_MS}\n\n"

    cached_messages: list[str] = []
    error_occurred = False

    try:
        async for log_entry in StockProcessor(symbol).run():
            log_html = format_log_entry(log_entry)
            cached_messages.append(log_html)

            if (
                log_entry.stage == ProcessingStage.COMPLETE
                and log_entry.status_type == StatusType.FAILED
            ):
                # Show the real reason (e.g. "No price data"); escaped because it may echo user input.
                reason = html.escape(" ".join((log_entry.message or "").split()))
                yield f"event: stream_error\ndata: {reason or _public_error_message(symbol)}\n\n"
                error_occurred = True
                break

            yield _sse_data(log_html)

        if cached_messages and not error_occurred:
            _save_stream_cache(symbol, cached_messages)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        yield f"event: stream_error\ndata: {_public_error_message(symbol, exc)}\n\n"
        error_occurred = True

    if not error_occurred:
        yield "event: complete\ndata: \n\n"


@app.get("/stream")
@limiter.limit("10/minute")
async def stream_symbol_logs(request: Request, symbol: str):
    """Stream log entries as Server-Sent Events."""
    return StreamingResponse(
        stream_logs(symbol),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/stream/mock")
async def stream_mock_symbol_logs(request: Request, symbol: str, delay_ms: int = 100):
    """Mock stream endpoint for fast frontend/UI iteration — never uses cache in dev."""
    return StreamingResponse(
        stream_mock_logs(symbol, cached_messages=None, delay_ms=delay_ms),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
