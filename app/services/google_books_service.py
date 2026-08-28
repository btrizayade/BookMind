import os

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.repositories.book_repository import BookRepository
from app.schemas.book import BookResponse
from app.services.gemini_service import generate_book_analysis


load_dotenv()


BASE_URL = "https://www.googleapis.com/books/v1/volumes"
API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

repository = BookRepository()


def search_books(title: str, db: Session):
    book = repository.get_by_title(db, title)

    if book:
        print("📚 Livro encontrado no banco.")

        # Gera a análise apenas se o livro ainda não tiver
        # resumo ou Book DNA.
        if not book.ai_summary or not book.book_dna:
            print("🤖 Gerando análise com IA...")

            analysis = generate_book_analysis(
                BookResponse(
                    title=book.title,
                    authors=book.authors.split(", "),
                    publisher=book.publisher,
                    page_count=book.page_count,
                    published_year=book.published_year,
                    language=book.language,
                    categories=(
                        book.categories.split(", ")
                        if book.categories
                        else []
                    ),
                    description=book.description,
                    preview_link=book.preview_link,
                    google_rating=book.google_rating,
                    ratings_count=book.ratings_count,
                    thumbnail=book.thumbnail,
                    ai_summary=book.ai_summary,
                    book_dna=book.book_dna,
                    source=book.source,
                )
            )

            # Só atualiza o banco se o Gemini conseguiu gerar a análise.
            if analysis:
                if analysis.get("summary"):
                    book.ai_summary = analysis["summary"]

                if analysis.get("book_dna"):
                    book.book_dna = analysis["book_dna"]

                db.commit()
                db.refresh(book)

            else:
                print("⚠️ Análise com IA indisponível.")

        return BookResponse(
            title=book.title,
            authors=book.authors.split(", "),
            publisher=book.publisher,
            page_count=book.page_count,
            published_year=book.published_year,
            language=book.language,
            categories=(
                book.categories.split(", ")
                if book.categories
                else []
            ),
            description=book.description,
            preview_link=book.preview_link,
            google_rating=book.google_rating,
            ratings_count=book.ratings_count,
            thumbnail=book.thumbnail,
            ai_summary=book.ai_summary,
            book_dna=book.book_dna,
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

    if not data.get("items"):
        return None

    book = data["items"][0]
    volume = book["volumeInfo"]

    book_response = _map_google_book(volume)

    analysis = generate_book_analysis(book_response)

# O livro continua sendo válido mesmo se o Gemini falhar.
    if analysis:
        book_response.ai_summary = analysis.get("summary")
        book_response.book_dna = analysis.get("book_dna")
    else:
        print("⚠️ Análise com IA indisponível.")

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
        book_dna=None,
        source="Google Books",
    )