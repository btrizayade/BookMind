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

# HS256 depends entirely on the secrecy and strength of this key.
# Refuse obviously weak production configuration at startup.
if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY deve ter pelo menos 32 caracteres."
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

    now = datetime.now(timezone.utc)

    expire = (
        now + expires_delta
        if expires_delta
        else now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
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
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                "require": ["sub", "iat", "exp", "type"],
            },
        )

        if payload.get("type") != "access":
            return None

        return payload

    except InvalidTokenError:
        return None