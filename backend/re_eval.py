import asyncio
from database import AsyncSessionLocal
from sqlalchemy.future import select
from models import Submission
from services.evaluation_service.worker import process_evaluation_task

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Submission).where(Submission.status == 'failed'))
        failed_subs = result.scalars().all()
        for sub in failed_subs:
            print(f'Re-evaluating {sub.id}...')
            sub.status = 'pending'
            await db.commit()
            await process_evaluation_task(sub.id)
            print(f'Done evaluating {sub.id}.')

if __name__ == '__main__':
    asyncio.run(main())
