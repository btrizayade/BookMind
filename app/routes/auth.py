import os
import secrets

import redis
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.security.auth import get_current_user
from app.security.jwt import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)
from app.security.password import hash_password, verify_password


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

repository = UserRepository()

ACCESS_TOKEN_COOKIE = "bookmind_access_token"
CSRF_COOKIE = "bookmind_csrf_token"

LOGIN_RATE_LIMIT = 5
LOGIN_RATE_WINDOW_SECONDS = 15 * 60
LOGIN_RATE_KEY_PREFIX = "bookmind:login-failures:"

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL and ENVIRONMENT == "production":
    raise RuntimeError(
        "REDIS_URL is required in production for login rate limiting."
    )

redis_client = (
    redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )
    if REDIS_URL
    else None
)


def _login_rate_key(email: str) -> str:
    return f"{LOGIN_RATE_KEY_PREFIX}{email}"


def _record_login_attempt(email: str) -> None:
    """
    Records a login attempt and blocks after too many attempts for the
    same normalized email within the configured window.
    """

    if redis_client is None:
        return

    key = _login_rate_key(email)

    try:
        pipeline = redis_client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, LOGIN_RATE_WINDOW_SECONDS)
        count, _ = pipeline.execute()

        if int(count) > LOGIN_RATE_LIMIT:
            ttl = redis_client.ttl(key)
            retry_after = max(int(ttl), 1)

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    except HTTPException:
        raise
    except redis.RedisError:
        # In production, failing open would silently disable protection.
        # Fail closed so Redis outages do not remove the rate limit.
        if ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable.",
            )


def _clear_login_attempts(email: str) -> None:
    """
    Clears failed-attempt state after a successful login.
    """

    if redis_client is None:
        return

    try:
        redis_client.delete(_login_rate_key(email))
    except redis.RedisError:
        # Clearing the counter is not required to keep the session secure.
        # Ignore cleanup failures so a successful login is not rejected.
        pass


def _set_csrf_cookie(response: Response) -> str:
    csrf_token = secrets.token_urlsafe(32)

    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=False,
        secure=True,
        samesite="none",
        path="/",
    )

    return csrf_token


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Cria uma nova conta de usuário.
    """

    email = user_data.email.strip().lower()

    existing_user = repository.get_by_email(
        db,
        email,
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create account. Please check your information and try again.",
        )

    password_hash = hash_password(
        user_data.password,
    )

    try:
        user = repository.create(
            db=db,
            name=user_data.name.strip(),
            email=email,
            password_hash=password_hash,
        )

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create account. Please check your information and try again.",
        )

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_active": user.is_active,
    }


@router.post(
    "/login",
)
def login(
    user_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Autentica um usuário e cria uma sessão segura em cookies.
    """

    email = user_data.email.strip().lower()

    _record_login_attempt(email)

    user = repository.get_by_email(
        db,
        email,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(
        user_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    _clear_login_attempts(email)

    access_token = create_access_token(
        subject=str(user.id),
    )

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )

    csrf_token = _set_csrf_cookie(response)

    return {
        "message": "Login successful.",
        "csrf_token": csrf_token,
    }


@router.get(
    "/csrf",
)
def get_csrf_token(response: Response):
    """
    Cria/renova o token CSRF para o frontend.

    O token CSRF não é um segredo de autenticação. Ele é devolvido ao
    frontend para que possa ser enviado no header X-CSRF-Token.
    """

    csrf_token = _set_csrf_cookie(response)

    return {
        "csrf_token": csrf_token,
    }


@router.post(
    "/logout",
)
def logout(response: Response):
    """
    Encerra a sessão removendo os cookies de autenticação e CSRF.
    """

    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path="/",
    )

    response.delete_cookie(
        key=CSRF_COOKIE,
        path="/",
    )

    return {
        "message": "Logout successful.",
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user=Depends(get_current_user),
):
    """
    Retorna os dados do usuário autenticado.
    """

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "is_active": current_user.is_active,
    }
