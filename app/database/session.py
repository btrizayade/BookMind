from sqlalchemy.orm import Session, sessionmaker

from app.database.database import engine


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()