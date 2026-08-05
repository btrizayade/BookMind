from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.book import BookResponse
from app.services.google_books_service import search_books

router = APIRouter()


@router.get("/books/search", response_model=BookResponse)
def search(title: str, db: Session = Depends(get_db)):
    return search_books(title, db)