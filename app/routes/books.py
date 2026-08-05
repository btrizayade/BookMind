from fastapi import APIRouter

from app.schemas.book import BookResponse
from app.services.google_books_service import search_books

router = APIRouter()


@router.get("/books/search", response_model=BookResponse)
def search(title: str):
    return search_books(title)