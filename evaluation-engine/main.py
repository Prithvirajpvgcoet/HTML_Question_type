import asyncio
from sandbox.pool_manager import sandbox_pool


async def main():
    print("[Evaluation Engine] Starting...")
    await sandbox_pool.start()
    print("[Evaluation Engine] Ready — waiting for jobs")
    # Phase 3: Celery/Redis queue consumer will be wired here
    await asyncio.sleep(2)
    await sandbox_pool.stop()
    print("[Evaluation Engine] Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())