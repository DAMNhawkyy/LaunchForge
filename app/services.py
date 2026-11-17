"""All database logic for users and startups.

Every private query includes user_id, so one user can never read or change
another user's plans.
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .errors import AppError
from .models import Startup, User
from .schemas import GeneratedPlan
from .security import hash_password, verify_password

PAGE_SIZE = 12


# ---- users ----
def create_user(db: Session, name: str, email: str, password: str) -> User:
    if db.scalar(select(User).where(User.email == email)):
        raise AppError(409, "An account with this email already exists", "EMAIL_TAKEN")
    user = User(name=name, email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    # Same message for "no such email" and "wrong password" (doesn't reveal which emails exist)
    if not user or not verify_password(password, user.password_hash):
        raise AppError(401, "Incorrect email or password", "BAD_LOGIN")
    return user


# ---- startups ----
def create_startup(db: Session, user_id: str, idea: str, plan: GeneratedPlan, is_public: bool) -> Startup:
    s = Startup(
        user_id=user_id,
        original_idea=idea,
        startup_name=plan.startupName,
        tagline=plan.tagline,
        elevator_pitch=plan.elevatorPitch,
        category=plan.category,
        generated_data=plan.model_dump(),
        is_public=is_public,
    )
    db.add(s)
    db.commit()
    return s


def list_user_startups(db: Session, user_id: str) -> list[Startup]:
    q = select(Startup).where(Startup.user_id == user_id).order_by(Startup.created_at.desc())
    return list(db.scalars(q))


def get_startup_for_viewer(db: Session, startup_id: str, user_id: str | None) -> Startup:
    s = db.get(Startup, startup_id)
    # Same 404 for "missing" and "private, not yours" so we don't leak existence.
    if not s or (not s.is_public and s.user_id != user_id):
        raise AppError(404, "Startup not found", "NOT_FOUND")
    return s


def get_owned_startup(db: Session, startup_id: str, user_id: str) -> Startup:
    s = db.scalar(select(Startup).where(Startup.id == startup_id, Startup.user_id == user_id))
    if not s:
        raise AppError(404, "Startup not found", "NOT_FOUND")
    return s


def toggle_public(db: Session, startup_id: str, user_id: str) -> Startup:
    s = get_owned_startup(db, startup_id, user_id)
    s.is_public = not s.is_public
    db.commit()
    return s


def delete_startup(db: Session, startup_id: str, user_id: str) -> None:
    db.delete(get_owned_startup(db, startup_id, user_id))
    db.commit()


def list_public_startups(db: Session, search: str | None, page: int):
    where = [Startup.is_public.is_(True)]
    term = (search or "").strip()
    if term:
        like = f"%{term}%"  # ilike = case-insensitive match; values are bound parameters (no SQL injection)
        where.append(or_(
            Startup.startup_name.ilike(like), Startup.tagline.ilike(like),
            Startup.category.ilike(like), Startup.elevator_pitch.ilike(like),
        ))
    total = db.scalar(select(func.count()).select_from(Startup).where(*where)) or 0
    items = db.scalars(
        select(Startup).where(*where).order_by(Startup.created_at.desc())
        .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )
    return list(items), total
