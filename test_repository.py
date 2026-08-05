from app.database.session import SessionLocal
from app.repositories.book_repository import BookRepository

db = SessionLocal()

repository = BookRepository()

book = repository.get_by_title(db, "Clean Code")

print(book.title)
print(book.publisher)
print(book.authors)