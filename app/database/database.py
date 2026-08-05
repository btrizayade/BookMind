from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = "sqlite:///bookmind.db"


engine = create_engine(DATABASE_URL)


class Base(DeclarativeBase):
    pass