import asyncio
import os
from playwright.async_api import async_playwright, Browser, BrowserContext

POOL_SIZE = int(os.getenv("SANDBOX_POOL_SIZE", 4))
TIMEOUT_MS = int(os.getenv("EVAL_TIMEOUT_MS", 30000))


class SandboxPool:
    def __init__(self):
        self._playwright = None
        self._browser: Browser = None
        self._semaphore = asyncio.Semaphore(POOL_SIZE)

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        print(f"[SandboxPool] Started — pool size: {POOL_SIZE}, timeout: {TIMEOUT_MS}ms")

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        print("[SandboxPool] Stopped")

    async def get_context(self) -> BrowserContext:
        """Acquire a semaphore slot + return a fresh isolated browser context."""
        await self._semaphore.acquire()
        return await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            java_script_enabled=True,
        )

    async def release_context(self, context: BrowserContext):
        """Close the context + release the semaphore slot."""
        try:
            await context.close()
        finally:
            self._semaphore.release()


sandbox_pool = SandboxPool()