from sqlalchemy import Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String)

    authors: Mapped[str] = mapped_column(String)

    publisher: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    published_year: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    categories: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    preview_link: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    google_rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    ratings_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    thumbnail: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    ai_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    book_dna: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    source: Mapped[str] = mapped_column(String)