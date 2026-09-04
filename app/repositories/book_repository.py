import re
import unicodedata

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.book import Book
from app.schemas.book import BookResponse


class BookRepository:

    # ========================================================
    # SAVE
    # ========================================================

    def save(
        self,
        db: Session,
        book: BookResponse,
    ) -> Book:
        """
        Salva um livro no banco.

        Antes de criar um novo registro, verifica se o livro
        já existe usando a lógica de equivalência de título.
        """

        existing_book = self.get_by_title(
            db,
            book.title,
        )

        if existing_book:
            return existing_book

        db_book = Book(
            title=book.title,
            authors=", ".join(book.authors),
            publisher=book.publisher,
            page_count=book.page_count,
            published_year=book.published_year,
            language=book.language,
            categories=(
                ", ".join(book.categories)
                if book.categories
                else None
            ),
            description=book.description,
            preview_link=book.preview_link,
            google_rating=book.google_rating,
            ratings_count=book.ratings_count,
            thumbnail=book.thumbnail,
            ai_summary=book.ai_summary,
            book_dna=book.book_dna,
            reading_profile=book.reading_profile,
            source=book.source,
        )

        db.add(db_book)
        db.commit()
        db.refresh(db_book)

        return db_book

    # ========================================================
    # GET BY TITLE
    # ========================================================

    def get_by_title(
        self,
        db: Session,
        title: str,
        author: str | None = None,
    ) -> Book | None:
        """
        Procura um livro pelo título.

        A busca acontece em duas etapas:

        1. Primeiro tenta encontrar o título exatamente.
        2. Depois tenta encontrar uma variação equivalente,
           como:

               The Metamorphosis
               The Metamorphosis, by Franz Kafka

        Quando um autor é informado, ele também é usado para
        confirmar que a variação realmente representa o mesmo
        livro.
        """

        if not title:
            return None

        # ----------------------------------------------------
        # 1. Busca exata
        # ----------------------------------------------------

        exact_book = (
            db.query(Book)
            .filter(
                func.lower(Book.title)
                == title.lower()
            )
            .first()
        )

        if exact_book:
            return exact_book

        # ----------------------------------------------------
        # 2. Busca por título equivalente
        # ----------------------------------------------------

        normalized_title = self._normalize_title(
            title
        )

        if not normalized_title:
            return None

        # Busca candidatos no banco.
        #
        # Não usamos apenas lower() aqui porque precisamos
        # considerar pontuação e pequenas variações de título.
        books = (
            db.query(Book)
            .all()
        )

        for book in books:

            book_normalized_title = self._normalize_title(
                book.title
            )

            # ------------------------------------------------
            # Título normalizado exatamente igual
            # ------------------------------------------------

            if (
                book_normalized_title
                == normalized_title
            ):
                return book

            # ------------------------------------------------
            # Título com "by Autor"
            # ------------------------------------------------

            if author:
                if self._titles_represent_same_book(
                    title,
                    book.title,
                    author,
                    book.authors,
                ):
                    return book

        return None

    # ========================================================
    # GET BOOKS FOR RECOMMENDATION
    # ========================================================

    def get_books_for_recommendation(
        self,
        db: Session,
    ) -> list[Book]:

        return (
            db.query(Book)
            .filter(
                Book.book_dna.isnot(None),
                Book.reading_profile.isnot(None),
            )
            .all()
        )

    # ========================================================
    # TITLE NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_title(
        title: str | None,
    ) -> str:
        """
        Normaliza um título para comparação.

        Exemplos:

            "The Metamorphosis"
            "the metamorphosis"
            "The Metamorphosis!"
            "The   Metamorphosis"

        tornam-se:

            "the metamorphosis"
        """

        if not title:
            return ""

        title = unicodedata.normalize(
            "NFKD",
            title,
        )

        title = "".join(
            char
            for char in title
            if not unicodedata.combining(char)
        )

        title = title.lower()

        # Remove pontuação.
        title = re.sub(
            r"[^\w\s]",
            " ",
            title,
        )

        # Remove espaços duplicados.
        title = re.sub(
            r"\s+",
            " ",
            title,
        ).strip()

        return title

    # ========================================================
    # SAME BOOK CHECK
    # ========================================================

    def _titles_represent_same_book(
        self,
        searched_title: str,
        database_title: str,
        searched_author: str,
        database_authors: str | None,
    ) -> bool:
        """
        Verifica se dois títulos provavelmente representam
        o mesmo livro.

        Exemplo aceito:

            The Metamorphosis
            The Metamorphosis, by Franz Kafka

        Exemplo que NÃO deve ser considerado igual:

            The Hunger Games
            The Hunger Games Trilogy

        O autor também precisa ser compatível.
        """

        normalized_searched = self._normalize_title(
            searched_title
        )

        normalized_database = self._normalize_title(
            database_title
        )

        normalized_searched_author = self._normalize_author(
            searched_author
        )

        normalized_database_authors = self._normalize_author(
            database_authors
        )

        if not normalized_searched:
            return False

        if not normalized_database:
            return False

        if not normalized_searched_author:
            return False

        if not normalized_database_authors:
            return False

        # ----------------------------------------------------
        # O autor precisa ser compatível.
        # ----------------------------------------------------

        if not self._authors_match(
            normalized_searched_author,
            normalized_database_authors,
        ):
            return False

        # ----------------------------------------------------
        # Se os títulos já são iguais depois da normalização,
        # são o mesmo livro.
        # ----------------------------------------------------

        if normalized_searched == normalized_database:
            return True

        # ----------------------------------------------------
        # Remove "by autor" SOMENTE quando o autor realmente
        # corresponde ao autor pesquisado.
        #
        # Exemplo:
        #
        # "the metamorphosis by franz kafka"
        #
        # vira:
        #
        # "the metamorphosis"
        # ----------------------------------------------------

        database_without_author = (
            self._remove_author_suffix(
                normalized_database,
                normalized_searched_author,
            )
        )

        searched_without_author = (
            self._remove_author_suffix(
                normalized_searched,
                normalized_searched_author,
            )
        )

        # ----------------------------------------------------
        # Compara novamente.
        # ----------------------------------------------------

        if (
            database_without_author
            == searched_without_author
        ):
            return True

        return False

    # ========================================================
    # REMOVE AUTHOR SUFFIX
    # ========================================================

    @staticmethod
    def _remove_author_suffix(
        title: str,
        author: str,
    ) -> str:
        """
        Remove um sufixo "by Autor" somente quando o texto
        realmente termina com o autor informado.

        Exemplo:

            the metamorphosis by franz kafka
            franz kafka

        retorna:

            the metamorphosis
        """

        if not title or not author:
            return title

        suffix = f" by {author}"

        if title.endswith(suffix):
            return title[
                : -len(suffix)
            ].strip()

        return title

    # ========================================================
    # AUTHOR MATCH
    # ========================================================

    @staticmethod
    def _normalize_author(
        author: str | None,
    ) -> str:
        """
        Normaliza o nome do autor.
        """

        if not author:
            return ""

        author = unicodedata.normalize(
            "NFKD",
            author,
        )

        author = "".join(
            char
            for char in author
            if not unicodedata.combining(char)
        )

        author = author.lower()

        author = re.sub(
            r"[^\w\s]",
            " ",
            author,
        )

        author = re.sub(
            r"\s+",
            " ",
            author,
        ).strip()

        return author

    @staticmethod
    def _authors_match(
        searched_author: str,
        database_authors: str,
    ) -> bool:
        """
        Verifica se o autor pesquisado corresponde ao autor
        armazenado no banco.
        """

        if not searched_author or not database_authors:
            return False

        # ----------------------------------------------------
        # Correspondência exata.
        # ----------------------------------------------------

        if searched_author == database_authors:
            return True

        searched_parts = set(
            searched_author.split()
        )

        database_parts = set(
            database_authors.split()
        )

        if not searched_parts or not database_parts:
            return False

        # ----------------------------------------------------
        # Verifica se todos os termos relevantes do autor
        # pesquisado aparecem no autor armazenado.
        # ----------------------------------------------------

        if searched_parts.issubset(database_parts):
            return True

        # ----------------------------------------------------
        # Verifica sobrenome.
        # ----------------------------------------------------

        searched_last_name = (
            searched_author.split()[-1]
        )

        database_author_names = (
            database_authors.split(",")
        )

        for database_author in database_author_names:

            database_parts = (
                database_author.strip().split()
            )

            if not database_parts:
                continue

            if (
                database_parts[-1]
                == searched_last_name
            ):
                return True

        return False