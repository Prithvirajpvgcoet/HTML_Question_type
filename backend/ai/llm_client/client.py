import asyncio
import json
import logging
import time
from google import genai
from google.genai import types
from config import settings

logger = logging.getLogger(__name__)

# Initialize the global client
client = genai.Client(api_key=settings.gemini_api_key)


class TokenBucket:
    """Asyncio token bucket rate limiter for RPM control."""
    def __init__(self, capacity: int, fill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.fill_rate = fill_rate
        self.last_fill = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1):
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_fill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
                self.last_fill = now
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                sleep_time = (tokens - self.tokens) / self.fill_rate
            await asyncio.sleep(sleep_time)


# Calculate tokens per second based on Requests Per Minute (RPM)
_tps = settings.llm_rpm_limit / 60.0
_rate_limiter = TokenBucket(capacity=settings.llm_rpm_limit, fill_rate=_tps)


def _build_thinking_config(thinking_level: str) -> types.ThinkingConfig | None:
    """
    Translate a simple string level into the correct ThinkingConfig for the
    model family we're on.

    gemini-3.x  → uses ThinkingLevel enum  (NONE / MINIMAL / LOW / HIGH)
    gemini-2.5x → uses thinking_budget int (0 = off, up to ~24576)

    We default to MINIMAL / budget=512 for generation (fast + mostly reliable
    schema-following) and NONE / 0 for scoring (pure extraction, no reasoning needed).
    """
    level = thinking_level.lower()

    # Map strings to enum values — these are the names exposed on the SDK
    level_map = {
        "none":    "NONE",
        "minimal": "MINIMAL",
        "low":     "LOW",
        "medium":  "MEDIUM",
        "high":    "HIGH",
    }

    try:
        # Gemini 3.x / Flash-Lite path: use ThinkingLevel enum
        enum_val = getattr(types.ThinkingLevel, level_map.get(level, "MINIMAL"), None)
        if enum_val is not None:
            return types.ThinkingConfig(thinking_level=enum_val)
    except AttributeError:
        pass

    # Fallback for Gemini 2.5 models that use budget integers
    budget_map = {"none": 0, "minimal": 512, "low": 1024, "medium": 4096, "high": 8192}
    budget = budget_map.get(level, 512)
    return types.ThinkingConfig(thinking_budget=budget)


async def call_llm_structured(
    system_prompt: str,
    user_message: str,
    schema: type | dict,
    model: str | None = None,
    thinking_level: str = "none",  # default to OFF — fast, reliable for JSON extraction
) -> dict | list:
    """
    Call Gemini with native JSON schema enforcement.

    thinking_level options: "none" | "minimal" | "low" | "medium" | "high"

    Use "none"    for scoring / simple extraction  (fastest, ~2–5s)
    Use "minimal" for assertion generation          (~8–20s, good schema compliance)
    Use "low"     for repair/diversify              (~15–30s, needs some reasoning)
    Use "high"    only if you really need deep reasoning (>30s, avoid for prod)
    """
    await _rate_limiter.consume(1)

    model_name = model or settings.llm_model_scoring
    thinking_cfg = _build_thinking_config(thinking_level)

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=schema,
        thinking_config=thinking_cfg,
        temperature=settings.llm_temperature,
    )

    t0 = time.monotonic()
    response = await client.aio.models.generate_content(
        model=model_name,
        contents=user_message,
        config=config,
    )
    elapsed = time.monotonic() - t0

    # Log usage + actual thinking tokens so we can confirm the budget is honoured
    if response.usage_metadata:
        thoughts = getattr(response.usage_metadata, "thoughts_token_count", None)
        logger.info(
            f"LLM call done [model={model_name} level={thinking_level} "
            f"elapsed={elapsed:.1f}s "
            f"in={response.usage_metadata.prompt_token_count} "
            f"out={response.usage_metadata.candidates_token_count} "
            f"thinking_tokens={thoughts}]"
        )
    else:
        logger.info(f"LLM call done [model={model_name} level={thinking_level} elapsed={elapsed:.1f}s]")

    raw = response.text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON from Gemini [model={model_name}]: {raw[:500]}")
        raise ValueError("LLM did not return valid JSON despite schema enforcement.")
