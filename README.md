# iMocha AI Eval

## Setup Instructions

### Database & Backend
1. Start PostgreSQL and Redis: cd docker && docker-compose up -d
2. Create and activate a Python virtual environment in ackend/
3. Install dependencies: pip install -r requirements.txt
4. Install Playwright browsers: playwright install --with-deps chromium
5. Run migrations: lembic upgrade head
6. Start FastAPI server: uvicorn main:app --reload --port 8000

### Frontends (Admin & Candidate)
The UI is split into two separate React applications.
1. Admin UI: cd frontend-admin && npm install --legacy-peer-deps && npm run dev
2. Candidate UI: cd frontend-candidate && npm install --legacy-peer-deps && npm run dev

### Environment Variables
Ensure you have a .env file in ackend/ with DATABASE_URL, REDIS_URL, and GEMINI_API_KEY.
Ensure you have .env.local files in the frontend directories with VITE_API_URL=http://localhost:8000/api/v1.
