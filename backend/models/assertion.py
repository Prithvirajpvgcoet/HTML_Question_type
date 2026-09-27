from typing import Optional
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum as SAEnum
from database import Base


class TriggerType(str, enum.Enum):
    page_load = "page_load"
    click = "click"
    change = "change"
    input = "input"
    hover = "hover"


class CheckType(str, enum.Enum):
    dom_presence = "dom_presence"
    computed_style = "computed_style"
    text_content = "text_content"
    attribute = "attribute"
    visual_region = "visual_region"


class ExecutionMode(str, enum.Enum):
    isolated = "isolated"
    sequential = "sequential"


class AssertionSource(str, enum.Enum):
    ai_generated = "ai_generated"
    author_added = "author_added"
    ai_edited = "ai_edited"


class Assertion(Base):
    __tablename__ = "assertions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    question_id: Mapped[str] = mapped_column(
        String, ForeignKey("questions.id"), nullable=False, index=True
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    trigger: Mapped[TriggerType] = mapped_column(SAEnum(TriggerType))
    trigger_selector: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    check_selector: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    wait_ms: Mapped[int] = mapped_column(Integer, default=300)
    check_type: Mapped[CheckType] = mapped_column(SAEnum(CheckType))
    expected_result: Mapped[str] = mapped_column(Text)
    points: Mapped[int] = mapped_column(Integer, default=10)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[AssertionSource] = mapped_column(
        SAEnum(AssertionSource), default=AssertionSource.ai_generated
    )
    
    execution_mode: Mapped[ExecutionMode] = mapped_column(SAEnum(ExecutionMode), default=ExecutionMode.sequential)
    group_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sequence_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    depends_on_state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    assertion_set_version: Mapped[int] = mapped_column(Integer, default=1)

    last_validation_status: Mapped[str] = mapped_column(String(20), default="not_run")
    last_validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


from sqlalchemy import DateTime
