import uuid
import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum as SAEnum
from database import Base


class ValidationStatus(str, enum.Enum):
    not_run = "not_run"
    passed = "passed"
    failed = "failed"


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(500))
    description_html: Mapped[str] = mapped_column(Text, nullable=True)  # rich-text HTML
    purpose: Mapped[str] = mapped_column(Text, nullable=True)
    question_type: Mapped[str] = mapped_column(String(100), default="HTML/CSS/JS")
    question_bank_name: Mapped[str] = mapped_column(String(300), nullable=True)

    # Reference solution (author's answer)
    reference_html: Mapped[str] = mapped_column(Text, nullable=True)
    reference_css: Mapped[str] = mapped_column(Text, nullable=True)
    reference_js: Mapped[str] = mapped_column(Text, nullable=True)

    # AI layer extensions
    validation_status: Mapped[ValidationStatus] = mapped_column(
        SAEnum(ValidationStatus), default=ValidationStatus.not_run
    )
    last_validation_results: Mapped[str] = mapped_column(Text, nullable=True)
    assertion_set_version: Mapped[int] = mapped_column(default=0)

    is_published: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    ) 