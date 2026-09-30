import uuid
from datetime import datetime, timedelta
from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class CandidateInvite(Base):
    __tablename__ = "candidate_invites"

    token: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.id"), nullable=False, index=True)
    candidate_name: Mapped[str] = mapped_column(String(300), nullable=False)
    candidate_email: Mapped[str] = mapped_column(String(300), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    used_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
