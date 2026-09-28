import secrets



from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.user_repository import UserRepository
from app.security.jwt import decode_access_token


ACCESS_TOKEN_COOKIE = "bookmind_access_token"
CSRF_COOKIE = "bookmind_csrf_token"
CSRF_HEADER = "X-CSRF-Token"

# Kept temporarily for backwards compatibility while the frontend is
# migrated from localStorage/Bearer authentication to secure cookies.
security = HTTPBearer(auto_error=False)
repository = UserRepository()


def _authentication_error(
    detail: str = "Invalid or expired authentication credentials.",
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _csrf_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid CSRF token.",
    )


def _validate_csrf(request: Request) -> None:
    """
    Validates the double-submit CSRF token for state-changing requests.

    The access token stays HttpOnly, while the CSRF token is intentionally
    readable by the frontend so it can be sent in a custom header.
    """

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        csrf_cookie = request.cookies.get(CSRF_COOKIE)
        csrf_header = request.headers.get(CSRF_HEADER)

        if (
            not csrf_cookie
            or not csrf_header
            or not secrets.compare_digest(csrf_cookie, csrf_header)
        ):
            raise _csrf_error()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Retorna o usuário autenticado a partir do JWT.

    Durante a migração, aceita o token no cookie HttpOnly e, caso ele ainda
    não exista, aceita temporariamente Authorization: Bearer.
    """

    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE)

    if cookie_token:
        token = cookie_token
        _validate_csrf(request)
    elif credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    else:
        raise _authentication_error()

    payload = decode_access_token(token)

    if not payload:
        raise _authentication_error()

    subject = payload.get("sub")

    if not subject:
        raise _authentication_error()

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _authentication_error()

    user = repository.get_by_id(
        db,
        user_id,
    )

    if not user:
        raise _authentication_error()

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user