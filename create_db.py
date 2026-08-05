from app.database.database import Base, engine
from app.models.book import Book

Base.metadata.create_all(bind=engine)

print("Banco criado com sucesso!")