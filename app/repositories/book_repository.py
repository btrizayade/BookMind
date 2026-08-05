from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.book import Book
from app.schemas.book import BookResponse


class BookRepository:

    def save(self, db: Session, book: BookResponse) -> Book:
        db_book = Book(
            title=book.title,
            authors=", ".join(book.authors),
            publisher=book.publisher,
            page_count=book.page_count,
            published_year=book.published_year,
            language=book.language,
            categories=", ".join(book.categories) if book.categories else None,
            description=book.description,
            preview_link=book.preview_link,
            google_rating=book.google_rating,
            ratings_count=book.ratings_count,
            thumbnail=book.thumbnail,
            ai_summary=book.ai_summary,
            source=book.source
        )

        db.add(db_book)
        db.commit()
        db.refresh(db_book)

        return db_book

    def get_by_title(self, db: Session, title: str) -> Book | None:
        return (
            db.query(Book)
            .filter(func.lower(Book.title) == title.lower())
            .first()
    )