import os
import re
import unicodedata

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.repositories.book_repository import BookRepository
from app.schemas.book import BookResponse
from app.services.gemini_service import generate_book_analysis
from app.services.openlibrary_service import search_book_metadata


load_dotenv()


BASE_URL = "https://www.googleapis.com/books/v1/volumes"
API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

repository = BookRepository()


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def _normalize_title(text: str | None) -> str:
    """
    Normaliza títulos para facilitar a comparação.
    """

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = text.lower()

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def _normalize_author(text: str | None) -> str:
    """
    Normaliza nomes de autores para facilitar a comparação.
    """

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = text.lower()

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


# ============================================================
# CONVERSÃO BOOK MODEL -> BOOK RESPONSE
# ============================================================

def _book_model_to_response(
    book,
) -> BookResponse:
    """
    Converte o model Book do banco para BookResponse.
    """

    return BookResponse(
        title=book.title,
        authors=(
            book.authors.split(", ")
            if book.authors
            else []
        ),
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
        reading_profile=book.reading_profile,
        source=book.source,
    )


# ============================================================
# GOOGLE BOOKS
# ============================================================

def _google_books_request(
    query: str,
) -> dict | None:
    """
    Faz uma requisição ao Google Books.

    Erros 5xx são tratados como indisponibilidade temporária,
    permitindo que o Open Library seja usado como fallback.
    """

    try:
        response = httpx.get(
            BASE_URL,
            params={
                "q": query,
                "maxResults": 10,
                "key": API_KEY,
            },
            timeout=20,
        )

        if response.status_code >= 500:
            print(
                f"⚠️ Google Books retornou "
                f"{response.status_code}."
            )
            return None

        response.raise_for_status()

        return response.json()

    except httpx.HTTPError as exc:
        print(
            f"⚠️ Google Books indisponível: {exc}"
        )
        return None


def _search_google_books(
    title: str,
    author: str | None = None,
) -> dict | None:
    """
    Consulta o Google Books usando buscas progressivamente
    mais abrangentes.
    """

    # --------------------------------------------------------
    # 1. TÍTULO + AUTOR
    # --------------------------------------------------------

    query = f'intitle:"{title}"'

    if author:
        query += f' inauthor:"{author}"'

    data = _google_books_request(
        query
    )

    if data and data.get("items"):
        volume = _select_best_volume(
            data["items"],
            title,
            author,
        )

        if volume:
            return volume

    # --------------------------------------------------------
    # 2. FALLBACK: TÍTULO
    # --------------------------------------------------------

    print(
        "🔎 Tentando busca por título..."
    )

    data = _google_books_request(
        f'intitle:"{title}"'
    )

    if data and data.get("items"):
        volume = _select_best_volume(
            data["items"],
            title,
            author,
        )

        if volume:
            return volume

    # --------------------------------------------------------
    # 3. FALLBACK: BUSCA GERAL
    # --------------------------------------------------------

    print(
        "🔎 Tentando busca geral..."
    )

    data = _google_books_request(
        title
    )

    if data and data.get("items"):
        volume = _select_best_volume(
            data["items"],
            title,
            author,
        )

        if volume:
            return volume

    return None


# ============================================================
# BUSCA DE LIVROS
# ============================================================

def search_books(
    title: str,
    db: Session,
    author: str | None = None,
):
    """
    Procura um livro:

    1. Primeiro no banco.
    2. Se os dados básicos estiverem incompletos,
       tenta completar com Google Books.
    3. Se ainda faltar informação, usa Open Library.
    4. Se não existir no banco, consulta Google Books.
    5. Usa Open Library como fallback de metadados.
    6. Gera Book DNA + Reading Profile com Gemini.
    7. Salva o livro.
    """

    # ========================================================
    # 1. BANCO DE DADOS
    # ========================================================

    book = repository.get_by_title(
        db,
        title,
        author,
    )

    if book:
        print(
            "📚 Livro encontrado no banco."
        )

        missing_basic_data = (
            not book.authors
            or not book.authors.strip()
            or not book.page_count
        )

        # ====================================================
        # COMPLETAR METADADOS
        # ====================================================

        if missing_basic_data:

            # ------------------------------------------------
            # GOOGLE BOOKS
            # ------------------------------------------------

            print(
                "⚠️ Dados básicos incompletos no banco."
            )

            try:
                print(
                    "🌐 Consultando Google Books "
                    "para completar..."
                )

                volume = _search_google_books(
                    title,
                    author,
                )

                if volume:

                    google_book = _map_google_book(
                        volume,
                        fallback_author=author,
                    )

                    if (
                        google_book.authors
                        and (
                            not book.authors
                            or not book.authors.strip()
                        )
                    ):
                        book.authors = ", ".join(
                            google_book.authors
                        )

                    if (
                        google_book.page_count
                        and not book.page_count
                    ):
                        book.page_count = (
                            google_book.page_count
                        )

                    if (
                        google_book.publisher
                        and not book.publisher
                    ):
                        book.publisher = (
                            google_book.publisher
                        )

                    if (
                        google_book.published_year
                        and not book.published_year
                    ):
                        book.published_year = (
                            google_book.published_year
                        )

                    if (
                        google_book.language
                        and not book.language
                    ):
                        book.language = (
                            google_book.language
                        )

                    if (
                        google_book.categories
                        and not book.categories
                    ):
                        book.categories = ", ".join(
                            google_book.categories
                        )

                    if (
                        google_book.description
                        and not book.description
                    ):
                        book.description = (
                            google_book.description
                        )

                    if (
                        google_book.preview_link
                        and not book.preview_link
                    ):
                        book.preview_link = (
                            google_book.preview_link
                        )

                    if (
                        google_book.thumbnail
                        and not book.thumbnail
                    ):
                        book.thumbnail = (
                            google_book.thumbnail
                        )

                    if (
                        google_book.google_rating
                        is not None
                        and book.google_rating is None
                    ):
                        book.google_rating = (
                            google_book.google_rating
                        )

                    if (
                        google_book.ratings_count
                        is not None
                        and book.ratings_count is None
                    ):
                        book.ratings_count = (
                            google_book.ratings_count
                        )

                    print(
                        "✅ Dados disponíveis do Google Books "
                        "foram aplicados."
                    )

            except Exception as exc:
                print(
                    f"⚠️ Erro ao completar com "
                    f"Google Books: {exc}"
                )

            # ------------------------------------------------
            # OPEN LIBRARY
            # ------------------------------------------------

            still_missing = (
                not book.authors
                or not book.authors.strip()
                or not book.page_count
            )

            if still_missing:

                print(
                    "🔎 Alguns dados continuam faltando."
                )

                try:
                    print(
                        "📚 Consultando Open Library..."
                    )

                    openlibrary_book = (
                        search_book_metadata(
                            title,
                            author,
                        )
                    )

                    if openlibrary_book:

                        if (
                            openlibrary_book.get(
                                "authors"
                            )
                            and (
                                not book.authors
                                or not book.authors.strip()
                            )
                        ):
                            book.authors = ", ".join(
                                openlibrary_book[
                                    "authors"
                                ]
                            )

                        if (
                            openlibrary_book.get(
                                "page_count"
                            )
                            and not book.page_count
                        ):
                            book.page_count = (
                                openlibrary_book[
                                    "page_count"
                                ]
                            )

                        if (
                            openlibrary_book.get(
                                "published_year"
                            )
                            and not book.published_year
                        ):
                            book.published_year = (
                                openlibrary_book[
                                    "published_year"
                                ]
                            )

                        print(
                            "✅ Dados faltantes "
                            "completados pelo Open Library."
                        )

                except Exception as exc:
                    print(
                        f"⚠️ Erro ao completar com "
                        f"Open Library: {exc}"
                    )

            # ------------------------------------------------
            # SALVA OS METADADOS COMPLETADOS
            # ------------------------------------------------

            db.commit()
            db.refresh(book)

        # ====================================================
        # GEMINI
        # ====================================================

        if (
            not book.ai_summary
            or not book.book_dna
            or not book.reading_profile
        ):
            print(
                "🤖 Gerando análise com IA..."
            )

            analysis = generate_book_analysis(
                _book_model_to_response(book)
            )

            if analysis:

                if analysis.get("summary"):
                    book.ai_summary = (
                        analysis["summary"]
                    )

                if analysis.get("book_dna"):
                    book.book_dna = (
                        analysis["book_dna"]
                    )

                if analysis.get(
                    "reading_profile"
                ):
                    book.reading_profile = (
                        analysis[
                            "reading_profile"
                        ]
                    )

                db.commit()
                db.refresh(book)

            else:
                print(
                    "⚠️ Análise com IA indisponível."
                )

        return _book_model_to_response(
            book
        )

    # ========================================================
    # 2. GOOGLE BOOKS
    # ========================================================

    print(
        "🌐 Consultando Google Books..."
    )

    volume = _search_google_books(
        title,
        author,
    )

    # ========================================================
    # SE GOOGLE BOOKS NÃO RETORNOU NADA
    # ========================================================

    if not volume:

        print(
            "⚠️ Google Books não encontrou "
            "um resultado adequado."
        )

        print(
            "📚 Tentando Open Library..."
        )

        openlibrary_book = search_book_metadata(
            title,
            author,
        )

        if not openlibrary_book:
            return None

        authors = (
            openlibrary_book.get(
                "authors"
            )
            or ([author] if author else [])
        )

        return BookResponse(
            title=(
                openlibrary_book.get(
                    "title"
                )
                or title
            ),
            authors=authors,
            publisher=None,
            page_count=openlibrary_book.get(
                "page_count"
            ),
            published_year=openlibrary_book.get(
                "published_year"
            ),
            language=None,
            categories=[],
            description=None,
            preview_link=None,
            google_rating=None,
            ratings_count=None,
            thumbnail=None,
            ai_summary=None,
            book_dna=None,
            reading_profile=None,
            source="Open Library",
        )

    # ========================================================
    # 3. CONVERSÃO
    # ========================================================

    print(
        f"📖 Resultado selecionado: "
        f"{volume.get('title')}"
    )

    book_response = _map_google_book(
        volume,
        fallback_author=author,
    )

    # ========================================================
    # 4. OPEN LIBRARY PARA COMPLETAR
    # ========================================================

    if (
        not book_response.authors
        or not book_response.page_count
    ):

        print(
            "🔎 Metadados incompletos no "
            "Google Books."
        )

        try:

            print(
                "📚 Consultando Open Library..."
            )

            openlibrary_book = (
                search_book_metadata(
                    title,
                    author,
                )
            )

            if openlibrary_book:

                if (
                    not book_response.authors
                    and openlibrary_book.get(
                        "authors"
                    )
                ):
                    book_response.authors = (
                        openlibrary_book[
                            "authors"
                        ]
                    )

                if (
                    not book_response.page_count
                    and openlibrary_book.get(
                        "page_count"
                    )
                ):
                    book_response.page_count = (
                        openlibrary_book[
                            "page_count"
                        ]
                    )

                if (
                    not book_response.published_year
                    and openlibrary_book.get(
                        "published_year"
                    )
                ):
                    book_response.published_year = (
                        openlibrary_book[
                            "published_year"
                        ]
                    )

                print(
                    "✅ Metadados completados "
                    "pelo Open Library."
                )

        except Exception as exc:
            print(
                f"⚠️ Erro ao consultar "
                f"Open Library: {exc}"
            )

    # ========================================================
    # 5. GEMINI
    # ========================================================

    analysis = generate_book_analysis(
        book_response
    )

    if analysis:

        book_response.ai_summary = (
            analysis.get("summary")
        )

        book_response.book_dna = (
            analysis.get("book_dna")
        )

        book_response.reading_profile = (
            analysis.get(
                "reading_profile"
            )
        )

    else:
        print(
            "⚠️ Análise com IA indisponível."
        )

    # ========================================================
    # 6. SALVA
    # ========================================================

    repository.save(
        db,
        book_response,
    )

    return book_response


# ============================================================
# SELEÇÃO DO MELHOR RESULTADO
# ============================================================

def _select_best_volume(
    items: list[dict],
    searched_title: str,
    searched_author: str | None = None,
) -> dict | None:
    """
    Seleciona o melhor resultado do Google Books.

    Prioridade:

    1. Título exato.
    2. Autor compatível.
    3. Presença de metadados.
    4. Melhor correspondência aproximada.

    Coleções, trilogias e guias são rejeitados.
    """

    normalized_search_title = (
        _normalize_title(
            searched_title
        )
    )

    # ========================================================
    # 1. TÍTULOS EXATOS
    # ========================================================

    exact_matches = []

    for item in items:

        volume = item.get(
            "volumeInfo",
            {},
        )

        result_title = volume.get(
            "title"
        )

        if not result_title:
            continue

        normalized_result_title = (
            _normalize_title(
                result_title
            )
        )

        if (
            normalized_result_title
            == normalized_search_title
        ):
            exact_matches.append(
                volume
            )

    if exact_matches:

        normalized_author = (
            _normalize_author(
                searched_author
            )
            if searched_author
            else ""
        )

        def exact_match_key(
            volume: dict,
        ):
            authors = volume.get(
                "authors",
                [],
            )

            author_score = (
                _calculate_author_score(
                    normalized_author,
                    authors,
                )
                if normalized_author
                else 0
            )

            metadata_score = (
                _metadata_completeness_score(
                    volume
                )
            )

            return (
                author_score,
                bool(authors),
                bool(volume.get("pageCount")),
                metadata_score,
                volume.get(
                    "ratingsCount"
                )
                or 0,
            )

        exact_matches.sort(
            key=exact_match_key,
            reverse=True,
        )

        best_volume = exact_matches[0]

        author_score = (
            _calculate_author_score(
                normalized_author,
                best_volume.get(
                    "authors",
                    [],
                ),
            )
            if normalized_author
            else 0
        )

        print(
            f"🔎 Match exato encontrado: "
            f"'{best_volume.get('title')}' "
            f"(score: 100.0)"
        )

        if searched_author:
            print(
                f"   👤 Autor pesquisado: "
                f"{searched_author}"
            )

        print(
            "   📊 Título: 100"
        )

        print(
            f"   📊 Autor: {author_score}"
        )

        if best_volume.get(
            "authors"
        ):
            print(
                "   ✅ Autor encontrado: "
                + ", ".join(
                    best_volume[
                        "authors"
                    ]
                )
            )
        else:
            print(
                "   ⚠️ Google Books não informou "
                "o autor."
            )

        if best_volume.get(
            "pageCount"
        ):
            print(
                f"   📄 Páginas: "
                f"{best_volume['pageCount']}"
            )
        else:
            print(
                "   ⚠️ Google Books não informou "
                "o número de páginas."
            )

        return best_volume

    # ========================================================
    # 2. TÍTULOS APROXIMADOS
    # ========================================================

    candidates = []

    for item in items:

        volume = item.get(
            "volumeInfo",
            {},
        )

        result_title = volume.get(
            "title"
        )

        if not result_title:
            continue

        if _is_collection_or_non_book_match(
            result_title,
            searched_title,
        ):
            print(
                f"⛔ Ignorando resultado inadequado: "
                f"'{result_title}'"
            )
            continue

        normalized_result_title = (
            _normalize_title(
                result_title
            )
        )

        title_score = (
            _calculate_title_score(
                normalized_search_title,
                normalized_result_title,
            )
        )

        if title_score < 40:
            continue

        author_score = (
            _calculate_author_score(
                _normalize_author(
                    searched_author
                ),
                volume.get(
                    "authors",
                    [],
                ),
            )
        )

        if searched_author:
            final_score = (
                title_score * 0.70
                + author_score * 0.30
            )
        else:
            final_score = title_score

        candidates.append(
            (
                final_score,
                title_score,
                author_score,
                bool(
                    volume.get(
                        "pageCount"
                    )
                ),
                _metadata_completeness_score(
                    volume
                ),
                volume,
            )
        )

    if not candidates:

        print(
            f"⚠️ Nenhum resultado adequado "
            f"encontrado para '{searched_title}'."
        )

        return None

    candidates.sort(
        key=lambda candidate: (
            candidate[0],
            candidate[1],
            candidate[2],
            candidate[3],
            candidate[4],
        ),
        reverse=True,
    )

    (
        best_score,
        title_score,
        author_score,
        _,
        _,
        best_volume,
    ) = candidates[0]

    print(
        f"🔎 Melhor correspondência: "
        f"'{best_volume.get('title')}' "
        f"(score: {best_score:.1f})"
    )

    if searched_author:
        print(
            f"   👤 Autor pesquisado: "
            f"{searched_author}"
        )

    print(
        f"   📊 Título: {title_score}"
    )

    print(
        f"   📊 Autor: {author_score}"
    )

    return best_volume


# ============================================================
# SCORE DO TÍTULO
# ============================================================

def _calculate_title_score(
    searched_title: str,
    result_title: str,
) -> int:
    """
    Calcula a correspondência aproximada entre títulos.
    """

    if not searched_title or not result_title:
        return 0

    if searched_title == result_title:
        return 100

    searched_words = set(
        searched_title.split()
    )

    result_words = set(
        result_title.split()
    )

    if not searched_words:
        return 0

    common_words = (
        searched_words.intersection(
            result_words
        )
    )

    overlap_score = (
        len(common_words)
        / len(searched_words)
    ) * 100

    extra_words = (
        result_words - searched_words
    )

    extra_penalty = min(
        len(extra_words) * 10,
        50,
    )

    score = (
        overlap_score
        - extra_penalty
    )

    return round(
        max(score, 0)
    )


# ============================================================
# SCORE DO AUTOR
# ============================================================

def _calculate_author_score(
    searched_author: str,
    result_authors: list[str],
) -> int:
    """
    Calcula a correspondência entre o autor pesquisado
    e os autores retornados.
    """

    if not searched_author or not result_authors:
        return 0

    normalized_search_author = (
        _normalize_author(
            searched_author
        )
    )

    for author in result_authors:

        normalized_result_author = (
            _normalize_author(
                author
            )
        )

        if not normalized_result_author:
            continue

        # Correspondência exata
        if (
            normalized_search_author
            == normalized_result_author
        ):
            return 100

        search_parts = (
            normalized_search_author.split()
        )

        result_parts = (
            normalized_result_author.split()
        )

        # Correspondência de sobrenome
        if (
            search_parts
            and result_parts
            and search_parts[-1]
            == result_parts[-1]
        ):
            return 70

        # Palavras em comum
        common_words = set(
            search_parts
        ).intersection(
            result_parts
        )

        if common_words:
            return 50

    return 0


# ============================================================
# COMPLETUDE DE METADADOS
# ============================================================

def _metadata_completeness_score(
    volume: dict,
) -> int:
    """
    Mede a quantidade de metadados úteis
    presentes no resultado.
    """

    return sum(
        [
            bool(
                volume.get(
                    "authors"
                )
            ),
            bool(
                volume.get(
                    "pageCount"
                )
            ),
            bool(
                volume.get(
                    "publishedDate"
                )
            ),
            bool(
                volume.get(
                    "publisher"
                )
            ),
            bool(
                volume.get(
                    "description"
                )
            ),
            bool(
                volume.get(
                    "categories"
                )
            ),
            bool(
                volume.get(
                    "imageLinks"
                )
            ),
            bool(
                volume.get(
                    "previewLink"
                )
            ),
            bool(
                volume.get(
                    "averageRating"
                )
            ),
            bool(
                volume.get(
                    "ratingsCount"
                )
            ),
        ]
    )


# ============================================================
# FILTRO DE COLEÇÕES / GUIAS
# ============================================================

def _is_collection_or_non_book_match(
    result_title: str,
    searched_title: str,
) -> bool:
    """
    Rejeita resultados que claramente representam
    coleções, trilogias, boxes, guias etc.
    """

    normalized_result = _normalize_title(
        result_title
    )

    normalized_searched = _normalize_title(
        searched_title
    )

    if (
        not normalized_result
        or not normalized_searched
    ):
        return False

    # Título exato nunca é rejeitado.
    if (
        normalized_result
        == normalized_searched
    ):
        return False

    unwanted_terms = {
        "trilogy",
        "collection",
        "box",
        "box set",
        "complete series",
        "complete collection",
        "omnibus",
        "bundle",
        "book set",
        "study guide",
        "conversation starters",
        "companion",
        "workbook",
        "analysis",
        "summary",
        "reader",
        "readers guide",
        "reading guide",
        "teacher guide",
        "teachers guide",
    }

    for term in unwanted_terms:

        normalized_term = _normalize_title(
            term
        )

        term_pattern = (
            rf"\b{re.escape(normalized_term)}\b"
        )

        if re.search(
            term_pattern,
            normalized_result,
        ):
            return True

    return False


# ============================================================
# GOOGLE BOOKS -> BOOK RESPONSE
# ============================================================

def _map_google_book(
    volume: dict,
    fallback_author: str | None = None,
) -> BookResponse:
    """
    Converte um volume do Google Books para BookResponse.

    Se o Google Books não informar o autor,
    utiliza o autor pesquisado como fallback.
    """

    authors = volume.get(
        "authors",
        [],
    )

    if (
        not authors
        and fallback_author
    ):
        authors = [
            fallback_author
        ]

    image_links = volume.get(
        "imageLinks",
        {},
    )

    return BookResponse(
        title=volume.get(
            "title"
        ),
        authors=authors,
        publisher=volume.get(
            "publisher"
        ),
        page_count=volume.get(
            "pageCount"
        )
        or None,
        published_year=volume.get(
            "publishedDate"
        ),
        language=volume.get(
            "language"
        ),
        categories=volume.get(
            "categories"
        )
        or [],
        description=volume.get(
            "description"
        ),
        preview_link=volume.get(
            "previewLink"
        ),
        google_rating=volume.get(
            "averageRating"
        ),
        ratings_count=volume.get(
            "ratingsCount"
        ),
        thumbnail=image_links.get(
            "thumbnail"
        ),
        ai_summary=None,
        book_dna=None,
        reading_profile=None,
        source="Google Books",
    )