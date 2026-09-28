import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. Set it in the environment before starting BookMind."
    )

is_sqlite = DATABASE_URL.startswith("sqlite")
is_postgresql = DATABASE_URL.startswith(
    ("postgresql://", "postgresql+psycopg://", "postgres://")
)

# SQLite is useful for local development, but BookMind must not silently
# fall back to it when the real database configuration is missing.
if is_sqlite and os.getenv("ENVIRONMENT", "development").lower() == "production":
    raise RuntimeError("SQLite is not allowed in production.")

connect_args = {}

if is_sqlite:
    connect_args["check_same_thread"] = False
elif is_postgresql:
    # Require TLS for PostgreSQL connections by default.
    # Set DB_SSLMODE explicitly for environments that need another mode.
    connect_args["sslmode"] = os.getenv("DB_SSLMODE", "require")

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=not is_sqlite,
)


class Base(DeclarativeBase):
    pass