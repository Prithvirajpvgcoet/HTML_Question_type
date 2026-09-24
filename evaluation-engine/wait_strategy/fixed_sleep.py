import asyncio


async def fixed_sleep(wait_ms: int):
    """Honour wait_ms before evaluating (for CSS transitions / JS timers)."""
    if wait_ms > 0:
        await asyncio.sleep(wait_ms / 1000.0)