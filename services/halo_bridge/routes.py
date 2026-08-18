from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("NoorBrain.HALO")

from services.noor_settings.service import noor_settings

router = APIRouter(prefix="/api/halo", tags=["HALO"])

OLLAMA_URL = os.getenv(
    "OLLAMA_GENERATE_URL",
    "http://127.0.0.1:11434/api/generate",
)
OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b",
)


class HaloChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


@router.get("/health")
async def halo_health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "halo_bridge",
        "model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_URL,
    }


@router.post("/chat")
async def halo_chat(
    payload: HaloChatRequest,
) -> dict[str, Any]:
    message = payload.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    settings = noor_settings.get_all()
    assistant_settings = settings.get("assistant", {})
    ai_settings = settings.get("ai", {})

    model = str(
        ai_settings.get("local_model")
        or OLLAMA_MODEL
    )

    context_size = max(
        256,
        min(
            int(ai_settings.get("context_size", 1024)),
            8192,
        ),
    )

    max_tokens = max(
        8,
        min(
            int(ai_settings.get("max_response_tokens", 40)),
            512,
        ),
    )

    assistant_name = str(
        assistant_settings.get("name")
        or "Noor"
    ).strip()

    response_style = str(
        assistant_settings.get("response_style")
        or "short"
    ).strip()

    request_body = {
        "model": model,
        "prompt": (
            f"You are {assistant_name}, the NoorBrain home AI assistant. "
            f"Response style: {response_style}. "
            "Answer naturally and do not repeat the question.\\n\\n"
            f"User: {message}\n"
            "HALO:"
        ),
        "stream": False,
        "keep_alive": "24h",
        "options": {
            "num_predict": max_tokens,
            "num_ctx": context_size,
            "temperature": 0.4,
            "top_p": 0.85
        },
    }

    timeout = httpx.Timeout(
        connect=10.0,
        read=180.0,
        write=30.0,
        pool=10.0,
    )

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
        ) as client:
            response = await client.post(
                OLLAMA_URL,
                json=request_body,
            )

        if response.status_code != 200:
            logger.error(
                "Ollama returned HTTP %s: %s",
                response.status_code,
                response.text[:1000],
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Ollama returned HTTP "
                    f"{response.status_code}: "
                    f"{response.text[:500]}"
                ),
            )

        try:
            result = response.json()
        except ValueError as exc:
            logger.exception(
                "Ollama returned invalid JSON"
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Ollama returned invalid JSON: "
                    f"{response.text[:500]}"
                ),
            ) from exc

        reply = str(
            result.get("response", "")
        ).strip()

        if not reply:
            logger.error(
                "Empty Ollama response: %r",
                result,
            )
            raise HTTPException(
                status_code=502,
                detail="Ollama returned an empty response.",
            )

        logger.info(
            "HALO response generated: model=%s input=%d output=%d",
            result.get("model", OLLAMA_MODEL),
            len(message),
            len(reply),
        )

        return {
            "status": "ok",
            "response": reply,
            "reply": reply,
            "model": result.get(
                "model",
                OLLAMA_MODEL,
            ),
            "done": bool(
                result.get("done", True)
            ),
        }

    except HTTPException:
        raise

    except httpx.ConnectError as exc:
        logger.exception(
            "HALO cannot connect to Ollama"
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Cannot connect to Ollama. "
                "Run: sudo systemctl restart ollama"
            ),
        ) from exc

    except httpx.TimeoutException as exc:
        logger.exception(
            "HALO Ollama request timed out"
        )
        raise HTTPException(
            status_code=504,
            detail=(
                "Ollama did not respond within "
                "180 seconds."
            ),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected HALO backend error"
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"HALO backend error: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc
