"""App entry point. Run with:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .database import Base, engine
from .errors import AppError, NotLoggedIn
from .routes import router, templates


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)  # creates the tables if they don't exist yet
    if settings.ai_mode == "mock":
        print("WARNING: AI_MODE=mock. Generated plans are simulated.")
    if settings.ai_mode == "gemini" and not settings.gemini_api_key:
        print("WARNING: GEMINI_API_KEY is not set; AI generation will fail.")
    yield


app = FastAPI(title="Launchforge", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# Login state is kept in a signed cookie (signed with SECRET_KEY, so it can't be forged).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",           # the browser won't send the cookie on cross-site POSTs (CSRF protection)
    https_only=settings.is_prod,
    max_age=60 * 60 * 24 * 7,  # 7 days
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; script-src-attr 'unsafe-inline'; form-action 'self'"
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return templates.TemplateResponse(
        request, "error.html",
        {"user": None, "status": exc.status_code, "message": exc.message},
        status_code=exc.status_code,
    )


@app.exception_handler(NotLoggedIn)
async def not_logged_in_handler(_request: Request, _exc: NotLoggedIn):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(404)
async def not_found_handler(request: Request, _exc):
    return templates.TemplateResponse(
        request, "error.html", {"user": None, "status": 404, "message": "Page not found"}, status_code=404
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    print("Unhandled error:", repr(exc))  # logged on the server only; the user sees a safe message
    return templates.TemplateResponse(
        request, "error.html",
        {"user": None, "status": 500, "message": "Something went wrong on our side"},
        status_code=500,
    )


app.include_router(router)
