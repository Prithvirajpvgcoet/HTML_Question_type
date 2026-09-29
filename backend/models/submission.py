import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    queued = "queued"
    evaluating = "evaluating"
    evaluated = "evaluated"
    completed = "completed"
    failed = "failed"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(
        String, ForeignKey("questions.id"), nullable=False, index=True
    )
    candidate_name: Mapped[str] = mapped_column(String(300), nullable=True)
    candidate_email: Mapped[str] = mapped_column(String(300), nullable=True)
    submitted_html: Mapped[str] = mapped_column(Text, nullable=True)
    submitted_css: Mapped[str] = mapped_column(Text, nullable=True)
    submitted_js: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        SAEnum(SubmissionStatus), default=SubmissionStatus.pending
    )
    tc_passed: Mapped[int] = mapped_column(Integer, default=0)
    tc_total: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    max_score: Mapped[int] = mapped_column(Integer, default=100)
    ai_feedback_text: Mapped[str] = mapped_column(Text, nullable=True)
    ai_feedback_breakdown: Mapped[str] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[str] = mapped_column(String(50), nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    evaluation_results = relationship(
        "EvaluationResult", back_populates="submission", cascade="all, delete-orphan"
    )
