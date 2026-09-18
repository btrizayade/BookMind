from datetime import datetime, timedelta, timezone
import os

import jwt
from dotenv import load_dotenv
from jwt.exceptions import InvalidTokenError


load_dotenv()


SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY não encontrada no arquivo .env."
    )


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Cria um access token JWT para o usuário.
    """

    expire = (
        datetime.now(timezone.utc) + expires_delta
        if expires_delta
        else datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": subject,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(
    token: str,
) -> dict | None:
    """
    Valida e decodifica um access token JWT.

    Retorna o payload quando o token é válido.
    Retorna None quando o token é inválido ou expirado.
    """

    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

    except InvalidTokenError:
        return None