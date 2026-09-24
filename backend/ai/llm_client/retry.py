import asyncio
import logging
from mistralai.models import SDKError

logger = logging.getLogger(__name__)

# Mistral's SDK raises a single SDKError for all non-2xx responses, with the
# HTTP status code on the exception (attribute name may be `status_code` or
# `.raw_response.status_code` depending on your pinned mistralai version --
# verify against the installed version and adjust _status_code() below).
RATE_LIMIT_STATUS = 429


def _status_code(err: SDKError) -> int | None:
    for attr in ("status_code", "http_status", "code"):
        val = getattr(err, attr, None)
        if isinstance(val, int):
            return val
    raw = getattr(err, "raw_response", None)
    return getattr(raw, "status_code", None) if raw is not None else None


async def with_retry(coro_fn, max_retries: int = 3, base_delay: float = 2.0):
    """Retry an async coroutine on rate-limit or transient Mistral API errors."""
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_fn()
        except SDKError as e:
            status = _status_code(e)
            if attempt == max_retries:
                raise
            if status == RATE_LIMIT_STATUS:
                wait = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Rate limit hit — retrying in {wait}s (attempt {attempt}/{max_retries})")
                await asyncio.sleep(wait)
            elif status is None or status >= 500:
                logger.warning(f"API error: {e} — retrying (attempt {attempt}/{max_retries})")
                await asyncio.sleep(base_delay)
            else:
                # 4xx that isn't a rate limit (bad request, auth, etc.) won't
                # succeed on retry — fail fast instead of burning attempts.
                raise