from sqlalchemy.orm import Session

from app.models.book import Book
from app.schemas.book import BookResponse

class BookRepository:

    def save(self, db: Session, book: BookResponse):
        pass