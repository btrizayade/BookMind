from app.database.session import SessionLocal
from app.services.google_books_service import search_books


# ============================================================
# LIVROS DO SEED
# ============================================================

BOOKS = [
    {
        "title": "The Metamorphosis",
        "author": "Franz Kafka",
    },
    {
        "title": "Animal Farm",
        "author": "George Orwell",
    },
    {
        "title": "The Little Prince",
        "author": "Antoine de Saint-Exupery",
    },
    {
        "title": "Coraline",
        "author": "Neil Gaiman",
    },
    {
        "title": "The Outsiders",
        "author": "S. E. Hinton",
    },
    {
        "title": "Wuthering Heights",
        "author": "Emily Bronte",
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
    },
    {
        "title": "The Picture of Dorian Gray",
        "author": "Oscar Wilde",
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
    },
    {
        "title": "The Hunger Games",
        "author": "Suzanne Collins",
    },
    {
        "title": "The Haunting of Hill House",
        "author": "Shirley Jackson",
    },
    {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
    },
    {
        "title": "Dune",
        "author": "Frank Herbert",
    },
    {
        "title": "The Fellowship of the Ring",
        "author": "J. R. R. Tolkien",
    },
]


# ============================================================
# SEED
# ============================================================

def seed_books():
    """
    Popula o banco com os livros definidos em BOOKS.

    A responsabilidade de:
    - procurar primeiro no banco;
    - consultar Google Books;
    - selecionar o melhor resultado;
    - usar Open Library como fallback;
    - gerar Book DNA / Reading Profile;
    - evitar duplicatas;

    fica nos serviços e repository.
    """

    db = SessionLocal()

    try:
        print("\n🌱 Iniciando seed dos livros...\n")

        for book_data in BOOKS:

            title = book_data["title"]
            author = book_data["author"]

            print(
                f"📚 {title} — {author}"
            )

            try:
                book = search_books(
                    title=title,
                    author=author,
                    db=db,
                )

                if not book:
                    print(
                        "   ❌ Livro não encontrado."
                    )
                    print()
                    continue

                print(
                    f"   ✓ Livro encontrado: "
                    f"{book.title} — "
                    f"{', '.join(book.authors)}"
                )

                if book.page_count:
                    print(
                        f"   📖 Páginas: "
                        f"{book.page_count}"
                    )
                else:
                    print(
                        "   📖 Páginas: Não informado"
                    )

                print(
                    "   🧬 Book DNA: "
                    + (
                        "✓"
                        if book.book_dna
                        else "✗"
                    )
                )

                print(
                    "   🎭 Reading Profile: "
                    + (
                        "✓"
                        if book.reading_profile
                        else "✗"
                    )
                )

            except Exception as error:
                print(
                    f"   ❌ Erro ao processar livro: "
                    f"{error}"
                )

            print()

        print("🌱 Seed finalizada!")

    finally:
        db.close()


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    seed_books()