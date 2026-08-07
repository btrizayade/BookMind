import os

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.repositories.book_repository import BookRepository
from app.schemas.book import BookResponse
from app.services.gemini_service import generate_summary

load_dotenv()

BASE_URL = "https://www.googleapis.com/books/v1/volumes"
API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

repository = BookRepository()


def search_books(title: str, db: Session):
    book = repository.get_by_title(db, title)

    if book:
        print("📚 Livro encontrado no banco.")

        # Atualiza o resumo caso esteja vazio
        # ou ainda esteja no formato antigo.
        if (
            book.description
            and (
                not book.ai_summary
                or "Why read this book?" not in book.ai_summary
            )
        ):
            print("🤖 Atualizando resumo com IA...")

            book.ai_summary = generate_summary(
                BookResponse(
                title=book.title,
                authors=book.authors.split(", "),
                publisher=book.publisher,
                page_count=book.page_count,
                published_year=book.published_year,
                language=book.language,
                categories=book.categories.split(", ") if book.categories else [],
                description=book.description,
                preview_link=book.preview_link,
                google_rating=book.google_rating,
                ratings_count=book.ratings_count,
                thumbnail=book.thumbnail,
                ai_summary=book.ai_summary,
                source=book.source,
    )
)

            db.commit()
            db.refresh(book)

        return BookResponse(
            title=book.title,
            authors=book.authors.split(", "),
            publisher=book.publisher,
            page_count=book.page_count,
            published_year=book.published_year,
            language=book.language,
            categories=book.categories.split(", ") if book.categories else [],
            description=book.description,
            preview_link=book.preview_link,
            google_rating=book.google_rating,
            ratings_count=book.ratings_count,
            thumbnail=book.thumbnail,
            ai_summary=book.ai_summary,
            source=book.source,
        )

    print("🌐 Consultando Google Books...")

    response = httpx.get(
        BASE_URL,
        params={
            "q": title,
            "key": API_KEY,
        },
    )

    response.raise_for_status()

    data = response.json()
    book = data["items"][0]
    volume = book["volumeInfo"]

    book_response = _map_google_book(volume)

    if book_response.description:
        book_response.ai_summary = generate_summary(
            book_response
        )

    repository.save(db, book_response)

    return book_response

def _map_google_book(volume: dict) -> BookResponse:
    return BookResponse(
        title=volume.get("title"),
        authors=volume.get("authors", []),
        publisher=volume.get("publisher"),
        page_count=volume.get("pageCount"),
        published_year=volume.get("publishedDate"),
        language=volume.get("language"),
        categories=volume.get("categories"),
        description=volume.get("description"),
        preview_link=volume.get("previewLink"),
        google_rating=volume.get("averageRating"),
        ratings_count=volume.get("ratingsCount"),
        thumbnail=volume.get("imageLinks", {}).get("thumbnail"),
        ai_summary=None,
        source="Google Books"
    )