# SPDX-License-Identifier: MIT
"""LLM factory — builds a CrewAI LLM instance using LiteLLM under the hood.

Switching providers requires only changing the LLM_MODEL env var.
If the primary model is an Ollama model and the Ollama endpoint is
unreachable, falls back to LLM_FALLBACK_MODEL automatically.
"""

import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

import litellm
from crewai import LLM

from src.core.config.config import (
    LLM_FALLBACK_MODEL,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    OLLAMA_BASE_URL,
)

litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("litellm").setLevel(logging.CRITICAL)

_log = logging.getLogger(__name__)


def _is_ollama_model(model: str) -> bool:
    return model.startswith("ollama/") or model.startswith("ollama_chat/")


def _ollama_reachable(base_url: str, model: str) -> bool:
    """Check if Ollama is running and has the requested model pulled."""
    if not base_url.startswith(("http://", "https://")):
        return False
    tags_url = f"{base_url.rstrip('/')}/api/tags"
    model_name = model.split("/", 1)[1].strip() if "/" in model else ""
    if not model_name:
        return False
    try:
        # Scheme is validated above; bandit B310 is a blanket warning on urlopen.
        with urlopen(Request(tags_url, method="GET"), timeout=3) as resp:  # nosec B310
            if not (200 <= resp.status < 300):
                return False
            payload = json.loads(resp.read().decode("utf-8"))
            available = {
                item.get("name", "").strip()
                for item in payload.get("models", [])
                if isinstance(item, dict)
            }
            return model_name in available
    except (URLError, TimeoutError, ValueError):
        return False


def _resolve_model() -> str:
    """Return the active model string, falling back if Ollama is unavailable."""
    if _is_ollama_model(LLM_MODEL) and not _ollama_reachable(OLLAMA_BASE_URL, LLM_MODEL):
        if LLM_FALLBACK_MODEL:
            _log.warning(
                "Ollama not ready (%s). Falling back to %s.",
                LLM_MODEL,
                LLM_FALLBACK_MODEL,
            )
            return LLM_FALLBACK_MODEL
    return LLM_MODEL


def get_llm() -> LLM:
    """Build a CrewAI LLM from config. LiteLLM handles provider routing."""
    active_model = _resolve_model()

    if "/" not in active_model or not active_model.split("/", 1)[1].strip():
        raise ValueError(
            f"Invalid LLM_MODEL format: '{active_model}'. Expected 'provider/model-name'."
        )

    kwargs: dict = {
        "model": active_model,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "timeout": LLM_TIMEOUT,
        "is_litellm": True,
    }

    if _is_ollama_model(active_model):
        kwargs["base_url"] = OLLAMA_BASE_URL
        # CrewAI's structured-output path can route through OpenAI parse APIs.
        # Passing provider-specific extras (like num_ctx) here may leak into that
        # call chain and raise unexpected-argument errors.

    return LLM(**kwargs)
