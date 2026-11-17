# Launchforge (Python edition)

Turns a one-line startup idea into a structured startup plan (pitch, personas, MVP features,
competitors, INR cost estimates, launch plan, risks). Users can register, save plans,
publish them to a public showcase, and browse other people's published plans.

**Stack:** Python 3.11+ · FastAPI · Jinja2 templates · SQLAlchemy (SQLite or PostgreSQL) ·
Pydantic validation · Google Gemini (`google-genai`) · pytest

## Folder map

| Path | What it does |
|---|---|
| `app/main.py` | Creates the app, cookies/sessions, security headers, error pages |
| `app/routes.py` | Every URL (login, generate, save, dashboard, explore...) |
| `app/ai_service.py` | Mock generator + real Gemini call + validation + retry. The ONLY file that talks to Gemini |
| `app/schemas.py` | Pydantic validation rules (shape of a plan, signup rules) |
| `app/services.py` | All database queries (users and startups) |
| `app/models.py` / `app/database.py` | Tables and DB connection |
| `app/security.py` | Password hashing + simple rate limiter |
| `app/config.py` | Reads `.env` settings |
| `app/templates/` | The HTML pages |
| `tests/` | Automated tests |

## Run it on Windows (PowerShell)

```powershell
cd C:\Users\Admin\Desktop\launchforge-py
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# open .env and set SECRET_KEY (see the comment inside it)
uvicorn app.main:app --reload
```

Open http://localhost:8000. If PowerShell blocks the activate script, run
`Set-ExecutionPolicy -Scope Process Bypass` once and try again.

The default `AI_MODE=mock` needs no key. For real AI, put your key in `.env`:

```
AI_MODE=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

## Run the tests

```powershell
python -m pytest -q
```

## Docker (app + PostgreSQL)

```powershell
copy .env.example .env      # if you have not already
docker compose up --build
```

Then open http://localhost:8000.

## Pages

`/` home · `/register` · `/login` · `/generate` (login needed) · `/dashboard` (login needed) ·
`/startups/<id>` (public plans for everyone, private plans for the owner only) · `/explore` · `/api/health`
