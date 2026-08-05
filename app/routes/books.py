from app.services.google_books_service import search_books
from fastapi import APIRouter

router = APIRouter()


@router.get("/books/search")
def search(title: str):
    return search_books(title)