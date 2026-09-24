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
                
                # Refill tokens
                self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
                self.last_fill = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # Calculate sleep time if we don't have enough tokens
                sleep_time = (tokens - self.tokens) / self.fill_rate
            
            # Wait outside the lock so other tasks can proceed when ready
            await asyncio.sleep(sleep_time)

# Calculate tokens per second based on Requests Per Minute (RPM)
_tps = settings.llm_rpm_limit / 60.0
# Global rate limiter instance
_rate_limiter = TokenBucket(capacity=settings.llm_rpm_limit, fill_rate=_tps)


async def call_llm_structured(
    system_prompt: str,
    user_message: str,
    schema: type | dict,
    model: str | None = None,
    thinking_level: str = "minimal"
) -> dict | list:
    """
    Call Gemini with native JSON schema enforcement and explicit thinking levels.
    Waits on a shared token bucket rate limiter to adhere to llm_rpm_limit.
    """
    # Wait for capacity in the rate limiter
    await _rate_limiter.consume(1)
    
    model_name = model or settings.llm_model_scoring

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema=schema,
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
        temperature=settings.llm_temperature
    )

    response = await client.aio.models.generate_content(
        model=model_name,
        contents=user_message,
        config=config
    )

    # Log usage
    if response.usage_metadata:
        logger.info(
            f"Usage [model={model_name}]: "
            f"Input={response.usage_metadata.prompt_token_count}, "
            f"Output={response.usage_metadata.candidates_token_count}"
        )

    # Parse response
    raw = response.text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON response from Gemini: {raw}")
        raise ValueError("LLM did not return valid JSON despite schema enforcement.")

