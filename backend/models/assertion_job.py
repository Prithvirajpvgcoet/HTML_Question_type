import enum
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum as SAEnum
from database import Base


class JobStatus(str, enum.Enum):
    queued = "queued"
    analyzing = "analyzing"
    validating = "validating"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AssertionGenerationJob(Base):
    __tablename__ = "assertion_generation_jobs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    question_id: Mapped[str] = mapped_column(
        String, ForeignKey("questions.id"), nullable=False, index=True
    )
    # "full" | "diversify" | "repair"
    mode: Mapped[str] = mapped_column(String(20), default="full")
    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus), default=JobStatus.queued
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON-serialized list of keep_assertion_ids (for diversify/repair)
    keep_assertion_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # JSON-serialized list of failed_assertion_ids (for repair)
    failed_assertion_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_count: Mapped[int] = mapped_column(Integer, default=6)
    # How many auto-repair rounds have been attempted for this question
    repair_round: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
