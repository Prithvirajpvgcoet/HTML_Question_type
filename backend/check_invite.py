import asyncio
from httpx import AsyncClient
from main import app
from httpx import ASGITransport

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        try:
            res = await client.get('/api/v1/invites/95bb61b0-bd90-47c8-9b2b-0e3864e079eb')
            print(res.status_code)
            print(res.text)
        except Exception as e:
            print("EXCEPTION:", e)

asyncio.run(main())
