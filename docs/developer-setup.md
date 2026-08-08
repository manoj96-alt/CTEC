# Developer Setup

Install Python 3.12+, Node.js 22+, and Docker Compose. Copy `.env.example` to `.env`. For native development, create a virtual environment in `cognitive-engine/backend`, run `pip install -e '.[dev]'`, then run `uvicorn app.main:app --reload`. In `cognitive-engine/frontend`, run `npm install` and `npm run dev`.

