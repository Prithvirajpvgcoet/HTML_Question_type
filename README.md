# iMocha AI Eval

## Setup Instructions

### Backend
1. Create a virtual environment: python -m venv .venv
2. Activate it: .\\.venv\\Scripts\\activate (Windows) or source .venv/bin/activate (Mac/Linux)
3. Install dependencies: pip install -r requirements.txt
4. **Install Playwright browsers**: playwright install --with-deps chromium

### Docker (Database & Redis)
Run docker-compose up -d from the docker/ directory to start PostgreSQL and Redis.
