from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.book import BookResponse
from app.services.google_books_service import search_books
from app.services.google_books_service import suggest_books


router = APIRouter()


@router.get(
    "/books/search",
    response_model=BookResponse,
)
def search(
    title: str,
    db: Session = Depends(get_db),
):
    """
    Busca um livro pelo título.
    """

    title = title.strip()

    if not title:
        return None

    return search_books(
        title,
        db,
    )


@router.get(
    "/books/suggest",
)
def suggest(
    q: str = Query(
        min_length=2,
        max_length=100,
    ),
    db: Session = Depends(get_db),
):
    """
    Retorna sugestões de livros para autocomplete.

    O endpoint é leve e não gera análise com IA.
    """

    query = q.strip()

    if len(query) < 2:
        return []

    return suggest_books(
        query,
        db,
    )