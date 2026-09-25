import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1.questions.crud import router as questions_router
from api.v1.submissions.crud import router as submissions_router
from api.v1.analytics.crud import router as analytics_router
from api.v1.invites.crud import router as invites_router

app = FastAPI(
    title="iMocha AI Evaluation API",
    version="0.2.0",
    description="AI-Assisted UI Evaluation for HTML/CSS/JS Questions",
)

# CRITICAL: CORS middleware MUST be registered BEFORE routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions_router, prefix="/api/v1/questions", tags=["Questions"])
app.include_router(submissions_router, prefix="/api/v1/submissions", tags=["Submissions"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(invites_router, prefix="/api/v1/invites", tags=["Invites"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "imocha-ai-eval", "version": "0.2.0"}

@app.post("/api/v1/webhook_stub")
async def webhook_stub(payload: dict):
    # Dummy endpoint to receive evaluation completion webhooks
    print(f"Received webhook: {payload}")
    return {"status": "received"}
