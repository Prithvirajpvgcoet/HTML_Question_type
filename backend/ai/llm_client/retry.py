import asyncio
import logging
from openai import RateLimitError, APIError

logger = logging.getLogger(__name__)


async def with_retry(coro_fn, max_retries: int = 3, base_delay: float = 2.0):
    """Retry an async coroutine on rate-limit or transient API errors."""
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_fn()
        except RateLimitError:
            if attempt == max_retries:
                raise
            wait = base_delay * (2 ** (attempt - 1))
            logger.warning(f"Rate limit hit — retrying in {wait}s (attempt {attempt}/{max_retries})")
            await asyncio.sleep(wait)
        except APIError as e:
            if attempt == max_retries:
                raise
            logger.warning(f"API error: {e} — retrying (attempt {attempt}/{max_retries})")
            await asyncio.sleep(base_delay)