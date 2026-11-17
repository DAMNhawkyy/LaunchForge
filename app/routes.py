"""All pages. Each function = one URL. They stay small: validate, call a service, render."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from . import services
from .ai_service import generate_startup_plan
from .config import settings
from .database import get_db
from .errors import AppError, NotLoggedIn
from .models import User
from .schemas import GeneratedPlan, IdeaIn, RegisterIn, SaveStartupIn
from .security import rate_limit

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))  # autoescapes HTML


# ---- helpers ----
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    return db.get(User, user_id) if user_id else None


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if not user:
        raise NotLoggedIn()
    return user


def first_error(e: ValidationError) -> str:
    """Turn a Pydantic error into one readable sentence."""
    err = e.errors()[0]
    field = str(err["loc"][-1]) if err["loc"] else "input"
    return f"{field}: {err['msg']}"


def page(request: Request, name: str, user: User | None, status_code: int = 200, **ctx):
    return templates.TemplateResponse(request, name, {"user": user, **ctx}, status_code=status_code)


# ---- general ----
@router.get("/api/health")
def health():
    return JSONResponse({"status": "ok"})


@router.get("/")
def home(request: Request, user: User | None = Depends(get_current_user)):
    return page(request, "index.html", user)


# ---- authentication ----
@router.get("/register")
def register_form(request: Request, user: User | None = Depends(get_current_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return page(request, "register.html", None, error=None, form={})


@router.post("/register")
def register(request: Request, name: str = Form(""), email: str = Form(""), password: str = Form(""),
             db: Session = Depends(get_db)):
    form = {"name": name, "email": email}
    try:
        data = RegisterIn(name=name, email=email, password=password)
        user = services.create_user(db, data.name, data.email, data.password)
    except ValidationError as e:
        msg = "Password must be at least 8 characters" if "password" in first_error(e) else first_error(e)
        return page(request, "register.html", None, 400, error=msg, form=form)
    except AppError as e:
        return page(request, "register.html", None, e.status_code, error=e.message, form=form)
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/login")
def login_form(request: Request, user: User | None = Depends(get_current_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return page(request, "login.html", None, error=None, form={})


@router.post("/login")
def login(request: Request, email: str = Form(""), password: str = Form(""), db: Session = Depends(get_db)):
    # Slow down password guessing: 10 attempts per 15 minutes per client address
    client = request.client.host if request.client else "unknown"
    try:
        rate_limit(f"login:{client}", 10, 15 * 60, "Too many login attempts. Try again in a few minutes.")
        user = services.authenticate(db, email, password)
    except AppError as e:
        return page(request, "login.html", None, e.status_code, error=e.message, form={"email": email})
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# ---- generating and saving ----
@router.get("/generate")
def generate_form(request: Request, user: User = Depends(require_user)):
    return page(request, "generate.html", user, idea="", plan=None, plan_json="", error=None)


@router.post("/generate")
def generate(request: Request, idea: str = Form(""), user: User = Depends(require_user)):
    # Plain "def" (not async) on purpose: FastAPI runs it in a worker thread,
    # so the slow AI call doesn't freeze the whole server.
    try:
        data = IdeaIn(idea=idea)
    except ValidationError:
        msg = "Please describe your idea in 10 to 1000 characters"
        return page(request, "generate.html", user, 400, idea=idea, plan=None, plan_json="", error=msg)
    rate_limit(f"generate:{user.id}", settings.generate_limit, 3600,
               f"Generation limit reached ({settings.generate_limit} per hour). Please try again later.")
    plan = generate_startup_plan(data.idea)
    return page(request, "generate.html", user, idea=data.idea, plan=plan,
                plan_json=plan.model_dump_json(), error=None)


@router.post("/startups")
def save_startup(request: Request, original_idea: str = Form(""), plan_json: str = Form(""),
                 is_public: str | None = Form(None), user: User = Depends(require_user),
                 db: Session = Depends(get_db)):
    try:
        data = SaveStartupIn(original_idea=original_idea, plan_json=plan_json, is_public=bool(is_public))
        plan = GeneratedPlan.model_validate_json(data.plan_json)  # never trust the browser: re-validate
    except ValidationError:
        raise AppError(400, "That plan could not be saved because it was incomplete", "VALIDATION_ERROR")
    s = services.create_startup(db, user.id, data.original_idea, plan, data.is_public)
    return RedirectResponse(f"/startups/{s.id}", status_code=303)


# ---- viewing, publishing, deleting ----
@router.get("/dashboard")
def dashboard(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return page(request, "dashboard.html", user, startups=services.list_user_startups(db, user.id))


@router.get("/startups/{startup_id}")
def view_startup(request: Request, startup_id: str, user: User | None = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    s = services.get_startup_for_viewer(db, startup_id, user.id if user else None)
    plan = GeneratedPlan.model_validate(s.generated_data)
    return page(request, "startup.html", user, s=s, plan=plan, is_owner=bool(user and s.user_id == user.id))


@router.post("/startups/{startup_id}/toggle-public")
def toggle_public(startup_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    services.toggle_public(db, startup_id, user.id)
    return RedirectResponse(f"/startups/{startup_id}", status_code=303)


@router.post("/startups/{startup_id}/delete")
def delete_startup(startup_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    services.delete_startup(db, startup_id, user.id)
    return RedirectResponse("/dashboard", status_code=303)


# ---- public showcase (no login needed) ----
@router.get("/explore")
def explore(request: Request, search: str = "", page_no: int = 1, user: User | None = Depends(get_current_user),
            db: Session = Depends(get_db)):
    search = search[:100]
    page_no = min(max(page_no, 1), 1000)
    items, total = services.list_public_startups(db, search, page_no)
    last_page = max(1, -(-total // services.PAGE_SIZE))  # ceiling division
    return page(request, "explore.html", user, items=items, total=total, search=search,
                page_no=page_no, last_page=last_page)
