from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from database import get_db
from models import Question, Submission
from models.submission import SubmissionStatus

router = APIRouter()

PASS_SCORE_THRESHOLD = 50  # Configurable pass threshold


@router.get("/summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    # Total questions
    q_count = await db.scalar(select(func.count()).select_from(Question)) or 0

    # Total submissions
    s_count = await db.scalar(select(func.count()).select_from(Submission)) or 0

    # Avg score (BUG-28 FIX: use Submission.total_score is not None)
    avg_score = await db.scalar(
        select(func.avg(Submission.total_score)).where(Submission.total_score.isnot(None))
    )

    # Pass rate (BUG-28 FIX: use and_() instead of multiple .where() positional args)
    # (BUG-29 FIX: use SubmissionStatus enum instead of bare string)
    passed_subs = await db.scalar(
        select(func.count()).select_from(Submission).where(
            and_(
                Submission.status == SubmissionStatus.completed,
                Submission.total_score >= PASS_SCORE_THRESHOLD
            )
        )
    ) or 0

    pass_rate = (passed_subs / s_count * 100) if s_count > 0 else 0

    return {
        "questions_count": q_count,
        "submissions_count": s_count,
        "avg_score": round(avg_score or 0),
        "pass_rate": round(pass_rate)
    }
