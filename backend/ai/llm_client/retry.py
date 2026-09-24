import asyncio
import logging
import random
from typing import Callable, TypeVar, Awaitable
from google.genai.errors import APIError

logger = logging.getLogger(__name__)
T = TypeVar('T')

async def with_retry(
    coro_fn: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 2.0
) -> T:
    """
    Retry an async operation with exponential backoff and jitter.
    Specifically catches google.genai.errors.APIError and retries on 429, 500, 503, 504.
    """
    for attempt in range(max_retries):
        try:
            return await coro_fn()
        except APIError as e:
            # e.code is typically populated with the HTTP status code
            status = getattr(e, 'code', None)
            
            if status in [429, 500, 503, 504]:
                if attempt == max_retries - 1:
                    logger.error(f"Max retries ({max_retries}) exhausted for API error: {status}")
                    raise
                
                # Exponential backoff with jitter
                delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                logger.warning(f"Google AI API error {status} - retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                # E.g., 400 Bad Request, 401 Unauthorized
                raise
        except Exception as e:
            # Do not retry on non-API errors (e.g., validation, JSON parse issues)
            raise
