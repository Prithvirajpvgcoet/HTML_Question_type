import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum
from database import Base


class TCStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    not_evaluated = "not_evaluated"


class LLMStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    not_evaluated = "not_evaluated"


class ReviewFlag(str, enum.Enum):
    none = "none"
    needs_review = "needs_review"
    overridden = "overridden"


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    submission_id: Mapped[str] = mapped_column(
        String, ForeignKey("submissions.id"), nullable=False, index=True
    )
    assertion_id: Mapped[str] = mapped_column(
        String, ForeignKey("assertions.id"), nullable=False
    )
    assertion_set_version: Mapped[int] = mapped_column(Integer, default=1)

    # Playwright result
    tc_status: Mapped[TCStatus] = mapped_column(
        SAEnum(TCStatus), default=TCStatus.not_evaluated
    )
    actual_result: Mapped[str] = mapped_column(Text, nullable=True)
    tc_evidence_url: Mapped[str] = mapped_column(String(1000), nullable=True)

    # LLM result
    llm_status: Mapped[LLMStatus] = mapped_column(
        SAEnum(LLMStatus), default=LLMStatus.not_evaluated
    )
    llm_evidence_text: Mapped[str] = mapped_column(Text, nullable=True)

    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    review_flag: Mapped[ReviewFlag] = mapped_column(
        SAEnum(ReviewFlag), default=ReviewFlag.none
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Back-reference to submission
    submission: Mapped["Submission"] = relationship(
        "Submission", back_populates="evaluation_results"
    )
