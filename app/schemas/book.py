from pydantic import BaseModel


class BookResponse(BaseModel):
    title: str
    authors: list[str]
    publisher: str | None = None
    page_count: int | None = None
    published_year: str | None = None
    language: str | None = None
    categories: list[str] | None = None
    description: str | None = None
    preview_link: str | None = None
    google_rating: float | None = None
    ratings_count: int | None = None
    thumbnail: str | None = None
    ai_summary: str | None = None
    book_dna: dict[str, int] | None = None
    reading_profile: dict[str, int] | None = None
    source: str