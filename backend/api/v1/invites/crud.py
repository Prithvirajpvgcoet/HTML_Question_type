from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from datetime import datetime, timezone
from database import get_db
from models import CandidateInvite

router = APIRouter()


class CreateInviteReq(BaseModel):
    question_id: str
    candidate_name: str
    candidate_email: str


@router.post("")
async def create_invite(req: CreateInviteReq, db: AsyncSession = Depends(get_db)):
    invite = CandidateInvite(
        question_id=req.question_id,
        candidate_name=req.candidate_name,
        candidate_email=req.candidate_email
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return {"token": invite.token}


@router.get("/{token}")
async def get_invite(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CandidateInvite).where(CandidateInvite.token == token))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Token not found")

    if invite.used_at is not None or invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invite invalid or expired")

    if invite.started_at is None:
        import datetime as dt
        invite.started_at = dt.datetime.now(dt.timezone.utc)
        await db.commit()

    # The deadline is started_at + 60 minutes
    from datetime import timedelta
    deadline = invite.started_at + timedelta(minutes=60)

    return {
        "question_id": invite.question_id,
        "candidate_name": invite.candidate_name,
        "candidate_email": invite.candidate_email,
        "started_at": invite.started_at,
        "deadline": deadline.isoformat() + "Z" if deadline.tzinfo is None else deadline.isoformat(),
        "used_at": invite.used_at
    }


@router.get("")
async def list_invites(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CandidateInvite))
    invites = result.scalars().all()
    return [{"token": i.token, "question_id": i.question_id, "candidate_name": i.candidate_name, "candidate_email": i.candidate_email, "expires_at": i.expires_at, "used_at": i.used_at} for i in invites]


@router.delete("/{token}")
async def revoke_invite(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CandidateInvite).where(CandidateInvite.token == token))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Token not found")
    await db.delete(invite)
    await db.commit()
    return {"message": "Token revoked"}
