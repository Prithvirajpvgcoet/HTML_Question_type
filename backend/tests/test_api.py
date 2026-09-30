import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

# This tells pytest to run these tests asynchronously
pytestmark = pytest.mark.asyncio

async def test_question_crud():
    """Test that we can create and retrieve a question"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create Question
        create_res = await client.post("/api/v1/questions", json={
            "title": "Test Question",
            "description_html": "<p>Build a box</p>"
        })
        assert create_res.status_code == 200
        q_id = create_res.json()["id"]
        
        # 2. Add Code Solution
        update_res = await client.put(f"/api/v1/questions/{q_id}/code-solution", json={
            "reference_html": "<div></div>",
            "reference_css": "",
            "reference_js": ""
        })
        assert update_res.status_code == 200
        
        # 3. Fetch it back
        get_res = await client.get(f"/api/v1/questions/{q_id}")
        assert get_res.status_code == 200
        assert get_res.json()["title"] == "Test Question"

async def test_llm_failure_handling():
    """Test that the API handles an invalid question ID gracefully"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Try to generate assertions for a non-existent question
        res = await client.post("/api/v1/questions/invalid-id-123/generate-assertions")
        # It should return a clean 404, not a 500 Internal Server Error crash
        assert res.status_code == 404

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from main import app
from database import AsyncSessionLocal
from models.candidate_invite import CandidateInvite
from sqlalchemy.future import select

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from main import app
from database import AsyncSessionLocal
from models.question import Question
from models.candidate_invite import CandidateInvite
from sqlalchemy.future import select

async def test_expired_invite_returns_400():
    # 1. Create a dummy question and expired invite
    async with AsyncSessionLocal() as db:
        q = Question(id='dummy-q-id-' + str(uuid.uuid4()), title='q', description_html='')
        db.add(q)
        await db.commit()
        
        expired_invite = CandidateInvite(
            token='expired-token-' + str(uuid.uuid4()),
            question_id='dummy-q-id-' + str(uuid.uuid4()),
            candidate_name='Test Name',
            candidate_email='test@example.com',
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(expired_invite)
        await db.commit()

    # 2. Hit the endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        res = await client.get(f'/api/v1/invites/{expired_invite.token}')
        assert res.status_code == 400
        assert res.json()['detail'] == 'Invite invalid or expired'
