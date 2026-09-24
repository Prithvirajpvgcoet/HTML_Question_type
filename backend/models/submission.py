import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum
from database import Base


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    queued = "queued"
    evaluating = "evaluating"
    evaluated = "evaluated"   # alias for completed - used by worker
    completed = "completed"
    failed = "failed"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    question_id: Mapped[str] = mapped_column(
        String, ForeignKey("questions.id"), nullable=False, index=True
    )

    candidate_name: Mapped[str] = mapped_column(String(300), nullable=True)
    candidate_email: Mapped[str] = mapped_column(String(300), nullable=True)

    submitted_html: Mapped[str] = mapped_column(Text, nullable=True)
    submitted_css: Mapped[str] = mapped_column(Text, nullable=True)
    submitted_js: Mapped[str] = mapped_column(Text, nullable=True)

    assertion_set_version: Mapped[int] = mapped_column(Integer, nullable=True)

    status: Mapped[SubmissionStatus] = mapped_column(
        SAEnum(SubmissionStatus), default=SubmissionStatus.pending
    )

    total_score: Mapped[int] = mapped_column(Integer, nullable=True)
    max_score: Mapped[int] = mapped_column(Integer, nullable=True)
    tc_passed: Mapped[int] = mapped_column(Integer, nullable=True)
    tc_total: Mapped[int] = mapped_column(Integer, nullable=True)
    llm_passed: Mapped[int] = mapped_column(Integer, nullable=True)
    llm_total: Mapped[int] = mapped_column(Integer, nullable=True)
    ai_confidence: Mapped[str] = mapped_column(String(20), nullable=True)
    ai_feedback_text: Mapped[str] = mapped_column(Text, nullable=True)
    ai_feedback_breakdown: Mapped[str] = mapped_column(Text, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relationship for eager loading
    evaluation_results: Mapped[list["EvaluationResult"]] = relationship(
        "EvaluationResult", back_populates="submission", lazy="select"
    )
