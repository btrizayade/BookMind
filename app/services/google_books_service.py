import os
import re
import unicodedata

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models.book import Book
from app.repositories.book_repository import BookRepository
from app.schemas.book import BookResponse
from app.services.gemini_service import generate_book_analysis
from app.services.openlibrary_service import search_book_metadata
from app.services.search_ranking import (
    is_viable_result,
    rank_book,
)

load_dotenv()


BASE_URL = "https://www.googleapis.com/books/v1/volumes"
API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

repository = BookRepository()


# Termos que normalmente indicam livros derivados, cópias SEO ou
# materiais que usam o nome da obra original como palavra-chave.
# Eles continuam sendo candidatos, mas devem ficar atrás de
# edições legítimas da obra pesquisada.
AUTOCOMPLETE_DERIVED_TERMS = {
    "advanced methods",
    "effective methods",
    "comprehensive beginner",
    "comprehensive guide to learn",
    "from a z",
    "from az",
    "learn the realms",
    "realms of",
    "blueprint",
    "methods and functions",
    "data structures for programming",
}


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def _normalize_title(
    text: str | None,
) -> str:
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


def normalize_text(value: str | None) -> str:
    """Alias compartilhado para normalizacao usada no autocomplete."""

    return _normalize_title(value)


def tokenize(value: str | None) -> list[str]:
    """Divide um texto normalizado em tokens."""

    normalized = normalize_text(value)

    if not normalized:
        return []

    return normalized.split()


def _normalize_author(
    text: str | None,
) -> str:
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
        themes=book.themes,
        atmosphere=book.atmosphere,
        story_elements=book.story_elements,
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
# SUGESTÕES DE AUTOCOMPLETE
# ============================================================

def _build_book_suggestion(
    volume: dict,
) -> dict | None:
    """
    Converte um volume do Google Books em uma sugestão leve.

    O autocomplete não gera análise com IA e mantém o volumeId
    do Google Books para que a seleção futura possa abrir a
    edição exata escolhida pelo usuário.
    """

    volume_id = volume.get("id")
    volume_info = volume.get("volumeInfo", {})

    title = volume_info.get("title")

    if not volume_id or not title:
        return None

    authors = volume_info.get("authors", [])

    return {
        "title": title,
        "subtitle": volume_info.get("subtitle"),
        "authors": authors,
        "author": authors[0] if authors else None,
        "year": volume_info.get("publishedDate"),
        "thumbnail": (
            volume_info.get(
                "imageLinks",
                {},
            ).get("thumbnail")
        ),
        "source": "google",
        "source_id": volume_id,
    }


def _build_database_suggestion(
    book: Book,
) -> dict:
    """
    Converte um livro salvo localmente em uma sugestão.
    """

    authors = (
        book.authors.split(", ")
        if book.authors
        else []
    )

    return {
        "title": book.title,
        "subtitle": None,
        "authors": authors,
        "author": authors[0] if authors else None,
        "year": book.published_year,
        "thumbnail": book.thumbnail,
        "source": "database",
        "source_id": str(book.id),
    }


def _autocomplete_quality_penalty(
    title: str,
    subtitle: str | None = None,
) -> float:
    """
    Penaliza sinais de resultados derivados ou excessivamente
    genéricos no autocomplete. Não elimina o resultado; apenas
    evita que ele ocupe uma das primeiras posições quando há
    edições mais relevantes.
    """

    text = " ".join(
        part
        for part in (title, subtitle)
        if part
    )
    normalized = normalize_text(text)

    penalty = 0.0

    for term in AUTOCOMPLETE_DERIVED_TERMS:
        if normalize_text(term) in normalized:
            penalty += 18.0

    # Subtítulos muito longos e genéricos tendem a ser menos úteis
    # para autocomplete do que subtítulos editoriais curtos, como
    # "An Illustrated Guide..." ou "Second Edition".
    subtitle_tokens = tokenize(subtitle)

    if len(subtitle_tokens) >= 11:
        penalty += min(
            (len(subtitle_tokens) - 10) * 1.5,
            10.0,
        )

    return min(penalty, 40.0)


def _autocomplete_text_score(
    query: str,
    title: str,
    subtitle: str | None = None,
) -> float:
    """
    Calcula um score específico para autocomplete.

    O autocomplete deve: 
    - privilegiar títulos que começam pela busca;
    - favorecer edições que tragam subtítulo útil;
    - evitar que títulos excessivamente longos e genéricos
      ocupem as primeiras posições;
    - permitir extensões legítimas como "Second Edition".
    """

    normalized_query = normalize_text(query)
    normalized_title = normalize_text(title)
    normalized_subtitle = normalize_text(subtitle)

    if not normalized_query or not normalized_title:
        return 0.0

    query_tokens = tokenize(normalized_query)
    title_tokens = tokenize(normalized_title)

    if not query_tokens or not title_tokens:
        return 0.0

    # --------------------------------------------------------
    # CORRESPONDÊNCIA PRINCIPAL
    # --------------------------------------------------------

    if normalized_title == normalized_query:
        score = 100.0
    elif normalized_title.startswith(normalized_query):
        score = 96.0
    elif normalized_query in normalized_title:
        score = 84.0
    else:
        query_token_set = set(query_tokens)
        title_token_set = set(title_tokens)

        matched_tokens = len(
            query_token_set.intersection(title_token_set)
        )

        for query_token in query_token_set - title_token_set:
            if any(
                token.startswith(query_token)
                or query_token.startswith(token)
                for token in title_token_set
            ):
                matched_tokens += 1

        token_ratio = matched_tokens / len(query_token_set)

        if token_ratio <= 0:
            return 0.0

        score = token_ratio * 65.0

    # --------------------------------------------------------
    # PREFIXO POR PALAVRAS
    # --------------------------------------------------------

    matched_prefix_tokens = 0

    for query_token, title_token in zip(
        query_tokens,
        title_tokens,
    ):
        if (
            query_token == title_token
            or query_token.startswith(title_token)
            or title_token.startswith(query_token)
        ):
            matched_prefix_tokens += 1
        else:
            break

    if matched_prefix_tokens:
        score += (
            matched_prefix_tokens
            / len(query_tokens)
        ) * 8.0

    # --------------------------------------------------------
    # TÍTULOS MUITO LONGOS
    # --------------------------------------------------------
    #
    # Pequenas extensões são perfeitamente normais:
    #
    #   Grokking Algorithms
    #   Grokking Algorithms, Second Edition
    #
    # Já extensões enormes e genéricas tendem a ser materiais
    # derivados, guias independentes ou livros que usam a obra
    # original apenas como palavra-chave.
    #
    # Não rejeitamos esses resultados; apenas os empurramos
    # para baixo no autocomplete.

    if normalized_title.startswith(normalized_query):
        extra_tokens = max(
            0,
            len(title_tokens) - len(query_tokens),
        )

        if extra_tokens > 1:
            score -= min(
                (extra_tokens - 1) * 2.5,
                24.0,
            )

    # --------------------------------------------------------
    # SUBTÍTULO ÚTIL
    # --------------------------------------------------------
    #
    # O subtítulo ajuda o usuário a diferenciar edições.
    # Ele recebe um pequeno bônus, suficiente para desempatar
    # uma edição rica em metadados sem dominar o ranking.

    if normalized_subtitle:
        score += 5.0

    # Se a consulta também aparece no subtítulo, há contexto
    # adicional, mas esse bônus é propositalmente pequeno.
    if normalized_subtitle and normalized_query in normalized_subtitle:
        score += 2.0

    return round(
        max(0.0, min(score, 100.0)),
        2,
    )

def _autocomplete_dedupe_key(
    suggestion: dict,
) -> tuple[str, str, str]:
    """
    Cria uma chave de deduplicação independente da fonte.

    Para o mesmo título/autor, uma entrada do banco e uma entrada
    do Google Books representam normalmente o mesmo livro. Nesses
    casos, mantemos a versão com metadados mais completos.
    """

    title = normalize_text(
        suggestion.get("title")
    )

    subtitle = normalize_text(
        suggestion.get("subtitle")
    )

    author = normalize_text(
        suggestion.get("author")
    )

    return (
        title,
        subtitle,
        author,
    )


def _suggestion_completeness(
    suggestion: dict,
) -> int:
    """Retorna um score simples de completude dos metadados."""

    fields = (
        suggestion.get("subtitle"),
        suggestion.get("author"),
        suggestion.get("year"),
        suggestion.get("thumbnail"),
    )

    return sum(
        bool(field)
        for field in fields
    )


def suggest_books(
    query: str,
    db: Session,
    limit: int = 4,
) -> list[dict]:
    """
    Retorna até quatro sugestões para autocomplete.

    Ordem lógica:

    1. livros locais;
    2. Google Books;
    3. deduplicação entre fontes;
    4. ranking específico de autocomplete;
    5. limite final de quatro sugestões.

    O endpoint não chama Gemini e não salva novos livros.
    """

    query = query.strip()

    if len(query) < 2:
        return []

    normalized_query = normalize_text(query)

    if not normalized_query:
        return []

    # A chave é independente da fonte para permitir deduplicação.
    merged: dict[tuple[str, str, str], tuple[float, dict]] = {}

    # ========================================================
    # 1. BANCO LOCAL
    # ========================================================

    local_books = (
        db.query(Book)
        .all()
    )

    for book in local_books:
        suggestion = _build_database_suggestion(book)

        score = _autocomplete_text_score(
            query,
            suggestion["title"],
            suggestion.get("subtitle"),
        )
        score -= _autocomplete_quality_penalty(
            suggestion["title"],
            suggestion.get("subtitle"),
        )

        if score < 35.0:
            continue

        key = _autocomplete_dedupe_key(
            suggestion
        )

        current = merged.get(key)

        # Quando o banco possui a mesma obra, Google Books poderá
        # substituir a entrada por uma versão com subtítulo/capa.
        if current is None:
            merged[key] = (
                score + 2.0,
                suggestion,
            )
            continue

        current_score, current_suggestion = current

        if (
            _suggestion_completeness(suggestion)
            > _suggestion_completeness(current_suggestion)
        ):
            merged[key] = (
                score,
                suggestion,
            )
        elif score > current_score:
            merged[key] = (
                score,
                suggestion,
            )

    # ========================================================
    # 2. GOOGLE BOOKS
    # ========================================================

    print(
        f"🔎 Autocomplete: consultando Google Books para '{query}'..."
    )

    data = _google_books_request(query)

    if data and data.get("items"):
        for item in data["items"]:
            volume_info = item.get(
                "volumeInfo",
                {},
            )

            result_title = volume_info.get("title")

            if not result_title:
                continue

            suggestion = _build_book_suggestion(item)

            if not suggestion:
                continue

            if _is_collection_or_non_book_match(
                result_title,
                query,
            ):
                continue

            score = _autocomplete_text_score(
                query,
                result_title,
                volume_info.get("subtitle"),
            )
            score -= _autocomplete_quality_penalty(
                result_title,
                volume_info.get("subtitle"),
            )

            # Ignora resultados sem relação suficiente.
            if score < 35.0:
                continue

            key = _autocomplete_dedupe_key(
                suggestion
            )

            current = merged.get(key)

            if current is None:
                merged[key] = (
                    score,
                    suggestion,
                )
                continue

            current_score, current_suggestion = current

            # Google Books geralmente tem subtítulo/capa/ID da edição,
            # então ganha quando possui metadados mais completos.
            google_completeness = _suggestion_completeness(
                suggestion
            )
            current_completeness = _suggestion_completeness(
                current_suggestion
            )

            if google_completeness > current_completeness:
                merged[key] = (
                    score,
                    suggestion,
                )
            elif score > current_score:
                merged[key] = (
                    score,
                    suggestion,
                )

    # ========================================================
    # 3. ORDENAÇÃO
    # ========================================================

    ranked = list(merged.values())

    ranked.sort(
        key=lambda item: (
            item[0],
            _suggestion_completeness(item[1]),
            1 if item[1].get("source") == "google" else 0,
            1 if item[1].get("subtitle") else 0,
            item[1].get("year") or "",
        ),
        reverse=True,
    )

    # ========================================================
    # 4. LIMITE FINAL
    # ========================================================

    result = [
        suggestion
        for _, suggestion in ranked[:4]
    ]

    print(
        f"✅ Autocomplete: {len(result)} sugestões retornadas."
    )

    for index, suggestion in enumerate(result, start=1):
        subtitle = suggestion.get("subtitle")
        label = suggestion["title"]

        if subtitle:
            label += f" — {subtitle}"

        print(
            f"   {index}. {label}"
            f" [{suggestion.get('author') or 'Autor desconhecido'}]"
            f" ({suggestion.get('source')})"
        )

    return result

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
    4. Busca subjects no Open Library.
    5. Se não existir no banco, consulta Google Books.
    6. Usa Open Library para metadados complementares.
    7. Gera análise completa com Gemini.
    8. Salva o livro.
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

        # ====================================================
        # COMPLETAR METADADOS
        # ====================================================

        missing_basic_data = (
            not book.authors
            or not book.authors.strip()
            or not book.page_count
        )

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

                    if google_book.page_count:
                        if (
                            not book.page_count
                            or not book.authors
                            or not book.authors.strip()
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
                            and (
                                not book.page_count
                                or not book.authors
                                or not book.authors.strip()
                            )
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

        # ====================================================
        # OPEN LIBRARY — SUBJECTS
        # ====================================================

        subjects = []

        try:
            print(
                "📚 Consultando Open Library "
                "para subjects..."
            )

            openlibrary_book = (
                search_book_metadata(
                    title,
                    author,
                )
            )

            if openlibrary_book:
                subjects = (
                    openlibrary_book.get(
                        "subjects",
                        [],
                    )
                )

        except Exception as exc:
            print(
                f"⚠️ Erro ao buscar subjects "
                f"no Open Library: {exc}"
            )

        # ====================================================
        # SALVA METADADOS
        # ====================================================

        db.commit()
        db.refresh(book)

        # ====================================================
        # GEMINI
        # ====================================================

        if (
            not book.ai_summary
            or not book.book_dna
            or not book.reading_profile
            or not book.themes
            or not book.atmosphere
            or not book.story_elements
        ):
            print(
                "🤖 Gerando análise completa com IA..."
            )

            book_response = _book_model_to_response(
                book
            )

            analysis = generate_book_analysis(
                book_response,
                subjects=subjects,
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

                if analysis.get("themes"):
                    book.themes = (
                        analysis["themes"]
                    )

                if analysis.get("atmosphere"):
                    book.atmosphere = (
                        analysis["atmosphere"]
                    )

                if analysis.get(
                    "story_elements"
                ):
                    book.story_elements = (
                        analysis[
                            "story_elements"
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

        openlibrary_book = (
            search_book_metadata(
                title,
                author,
            )
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
            themes=None,
            atmosphere=None,
            story_elements=None,
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
    # 4. OPEN LIBRARY — COMPLETAR + SUBJECTS
    # ========================================================

    openlibrary_book = None
    subjects = []

    try:
        print(
            "📚 Consultando Open Library "
            "para dados complementares..."
        )

        openlibrary_book = (
            search_book_metadata(
                title,
                author,
            )
        )

        if openlibrary_book:

            subjects = (
                openlibrary_book.get(
                    "subjects",
                    [],
                )
            )

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
                "✅ Metadados complementares "
                "do Open Library processados."
            )

    except Exception as exc:
        print(
            f"⚠️ Erro ao consultar "
            f"Open Library: {exc}"
        )

    # ========================================================
    # 5. GEMINI — ANÁLISE COMPLETA
    # ========================================================

    analysis = generate_book_analysis(
        book_response,
        subjects=subjects,
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

        book_response.themes = (
            analysis.get("themes")
        )

        book_response.atmosphere = (
            analysis.get("atmosphere")
        )

        book_response.story_elements = (
            analysis.get(
                "story_elements"
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
    Seleciona o resultado mais relevante do Google Books.

    O ranking considera:
    - correspondência do título;
    - correspondência por prefixo;
    - palavras em comum;
    - ordem das palavras;
    - autor;
    - qualidade dos metadados;
    - penalidades para guias, coleções e materiais
      complementares.

    Um título completo que começa com a pesquisa pode ser
    considerado mais relevante do que uma versão curta
    aparentemente exata.
    """

    candidates = []

    for item in items:
        volume = item.get("volumeInfo", {})

        result_title = volume.get("title")

        if not result_title:
            continue

        # ----------------------------------------------------
        # FILTRO DE RESULTADOS INADEQUADOS
        # ----------------------------------------------------

        if _is_collection_or_non_book_match(
            result_title,
            searched_title,
        ):
            print(
                f"⛔ Ignorando resultado inadequado: "
                f"'{result_title}'"
            )
            continue

        # ----------------------------------------------------
        # VALIDAÇÃO MÍNIMA DO TÍTULO
        # ----------------------------------------------------

        if not is_viable_result(
            searched_title,
            result_title,
        ):
            print(
                f"⛔ Correspondência muito fraca: "
                f"'{result_title}'"
            )
            continue

        # ----------------------------------------------------
        # RANKING
        # ----------------------------------------------------

        rank = rank_book(
            searched_title=searched_title,
            result_title=result_title,
            searched_author=searched_author,
            result_authors=volume.get("authors", []),
            page_count=volume.get("pageCount"),
            publisher=volume.get("publisher"),
            thumbnail=(
                volume.get("imageLinks", {})
                .get("thumbnail")
            ),
            published_year=volume.get(
                "publishedDate"
            ),
        )

        candidates.append(
            (
                rank,
                volume,
            )
        )

    # --------------------------------------------------------
    # NENHUM CANDIDATO
    # --------------------------------------------------------

    if not candidates:
        print(
            f"⚠️ Nenhum resultado adequado "
            f"encontrado para '{searched_title}'."
        )

        return None

    # --------------------------------------------------------
    # ORDENAÇÃO
    # --------------------------------------------------------

    candidates.sort(
        key=lambda candidate: (
            candidate[0].total_score,
            candidate[0].title_score,
            candidate[0].author_score,
            candidate[0].quality_score,
        ),
        reverse=True,
    )

    best_rank, best_volume = candidates[0]

    # --------------------------------------------------------
    # LOGS
    # --------------------------------------------------------

    print(
        f"🔎 Melhor correspondência: "
        f"'{best_volume.get('title')}' "
        f"(score: {best_rank.total_score:.2f})"
    )

    print(
        f"   📊 Título: "
        f"{best_rank.title_score:.2f}"
    )

    print(
        f"   👤 Autor: "
        f"{best_rank.author_score:.2f}"
    )

    print(
        f"   📚 Qualidade dos metadados: "
        f"{best_rank.quality_score:.2f}"
    )

    if best_rank.penalties > 0:
        print(
            f"   ⚠️ Penalidades: "
            f"-{best_rank.penalties:.2f}"
        )

    if searched_author:
        print(
            f"   👤 Autor pesquisado: "
            f"{searched_author}"
        )

    if best_volume.get("authors"):
        print(
            "   ✅ Autor encontrado: "
            + ", ".join(
                best_volume["authors"]
            )
        )

    if best_volume.get("pageCount"):
        print(
            f"   📄 Páginas: "
            f"{best_volume['pageCount']}"
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
        themes=None,
        atmosphere=None,
        story_elements=None,
        source="Google Books",
    )