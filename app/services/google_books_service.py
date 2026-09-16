import os
import re
import time
import unicodedata
import threading
from concurrent.futures import ThreadPoolExecutor

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
OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPENLIBRARY_COVERS_URL = "https://covers.openlibrary.org/b/id"
API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")

repository = BookRepository()

# Cliente HTTP compartilhado para reutilizar conexões TCP/TLS entre requisições.
_http_client = httpx.Client()


# Termos que normalmente indicam livros derivados, cópias SEO ou
# materiais que usam o nome da obra original como palavra-chave.
# Eles continuam sendo candidatos, mas devem ficar atrás de
# edições legítimas da obra pesquisada.
AUTOCOMPLETE_DERIVED_TERMS = {
    # English — likely complementary/SEO/derived material
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
    "study guide",
    "reading guide",
    "teacher guide",
    "teachers guide",
    "conversation starters",
    "workbook",
    "companion",
    "analysis",
    "summary",
    "philosophy",
    "analysis book",

    # Portuguese — likely complementary/derived material
    "análise",
    "resumo",
    "filosofia",
    "guia de estudo",
    "guia de leitura",
    "guia do professor",
    "trilogia",
    "saga",
    "coleção",
    "manual",
}



# Cache curto para autocomplete.
# A ideia é evitar repetir chamadas ao Google Books durante a mesma sessão
# e aproveitar consultas que o usuário acabou de fazer.
AUTOCOMPLETE_CACHE_TTL = 300
_autocomplete_cache: dict[str, tuple[float, list[dict]]] = {}

# Termos/expressões que normalmente identificam materiais complementares
# e coleções, em vez da obra procurada. Mantemos termos genéricos como
# "guide" e "philosophy" fora desta lista para não eliminar livros legítimos.
AUTOCOMPLETE_HARD_EXCLUDE_TERMS = {
    "trilogy",
    "collection",
    "box set",
    "complete series",
    "complete collection",
    "omnibus",
    "bundle",
    "book set",
    "study guide",
    "reading guide",
    "teacher guide",
    "teachers guide",
    "conversation starters",
    "workbook",
    "companions",
    "companion",
    "trilogia",
    "coleção",
    "box",
    "kit",
    "guia de estudo",
    "guia de leitura",
    "guia do professor",
    "resumo completo",
    "análise completa",
    "analise completa",
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
        response = _http_client.get(
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
# AUTOCOMPLETE
# ============================================================

# Cache curto em memória. O autocomplete trabalha com prefixos e,
# por isso, consultas recentes são muito reaproveitáveis.
AUTOCOMPLETE_CACHE_TTL = 300
AUTOCOMPLETE_SOURCE_LIMIT = 6
AUTOCOMPLETE_MAX_RESULTS = 4
AUTOCOMPLETE_TIMEOUT = 2.8

_autocomplete_cache: dict[str, tuple[float, object]] = {}
_autocomplete_cache_lock = threading.Lock()

OPENLIBRARY_HEADERS = {
    "User-Agent": "BookMind/1.0 (book discovery application)",
}


def _autocomplete_cache_get(
    key: str,
) -> object | None:
    """Retorna um valor válido do cache, removendo entradas expiradas."""

    now = time.monotonic()

    with _autocomplete_cache_lock:
        cached = _autocomplete_cache.get(key)

        if not cached:
            return None

        cached_at, value = cached

        if now - cached_at >= AUTOCOMPLETE_CACHE_TTL:
            _autocomplete_cache.pop(key, None)
            return None

        return value


def _autocomplete_cache_set(
    key: str,
    value: object,
) -> None:
    """Salva um valor no cache do autocomplete."""

    with _autocomplete_cache_lock:
        _autocomplete_cache[key] = (
            time.monotonic(),
            value,
        )


def _openlibrary_autocomplete_request(
    query: str,
) -> list[dict]:
    """
    Descobre candidatos no Open Library.

    O Search API trabalha no nível de Work, mas também pode devolver
    informações de Edition por meio do campo `editions`. Aproveitamos
    isso para tentar obter capa/autor/edição sem uma segunda chamada.
    """

    normalized_query = normalize_text(query)

    if not normalized_query:
        return []

    cache_key = f"openlibrary:{normalized_query}"
    cached = _autocomplete_cache_get(cache_key)

    if cached is not None:
        return cached  # type: ignore[return-value]

    fields = (
        "key,title,subtitle,author_name,first_publish_year,cover_i,"
        "edition_count,editions.key,editions.title,editions.cover_i,"
        "editions.author_name,editions.publish_date"
    )

    try:
        response = httpx.get(
            OPENLIBRARY_SEARCH_URL,
            params={
                "title": query,
                "limit": AUTOCOMPLETE_SOURCE_LIMIT,
                "fields": fields,
            },
            headers=OPENLIBRARY_HEADERS,
            timeout=AUTOCOMPLETE_TIMEOUT,
        )

        # Algumas mudanças no schema de fields podem provocar 400.
        # Nesse caso, mantemos o autocomplete funcional com Work metadata.
        if response.status_code == 400:
            response = httpx.get(
                OPENLIBRARY_SEARCH_URL,
                params={
                    "title": query,
                    "limit": AUTOCOMPLETE_SOURCE_LIMIT,
                    "fields": (
                        "key,title,subtitle,author_name,"
                        "first_publish_year,cover_i,edition_count"
                    ),
                },
                headers=OPENLIBRARY_HEADERS,
                timeout=AUTOCOMPLETE_TIMEOUT,
            )

        response.raise_for_status()
        data = response.json()
        results = data.get("docs", [])

        _autocomplete_cache_set(cache_key, results)
        return results

    except (httpx.HTTPError, ValueError) as exc:
        print(
            f"⚠️ Open Library autocomplete indisponível: {exc}"
        )
        return []


def _google_books_autocomplete_request(
    query: str,
) -> list[dict]:
    """
    Descobre candidatos no Google Books.

    O Google é usado aqui como fonte de descoberta e, principalmente,
    de metadados bibliográficos confiáveis para o card do autocomplete.
    """

    normalized_query = normalize_text(query)

    if not normalized_query:
        return []

    cache_key = f"google:{normalized_query}"
    cached = _autocomplete_cache_get(cache_key)

    if cached is not None:
        return cached  # type: ignore[return-value]

    if not API_KEY:
        print(
            "⚠️ Google Books autocomplete ignorado: API key ausente."
        )
        _autocomplete_cache_set(cache_key, [])
        return []

    try:
        response = httpx.get(
            BASE_URL,
            params={
                "q": f'intitle:"{query}"',
                "maxResults": AUTOCOMPLETE_SOURCE_LIMIT,
                "printType": "books",
                "key": API_KEY,
                "fields": (
                    "items(id,volumeInfo(title,subtitle,authors,"
                    "publishedDate,imageLinks,industryIdentifiers,"
                    "pageCount,publisher,averageRating,ratingsCount))"
                ),
            },
            timeout=AUTOCOMPLETE_TIMEOUT,
        )

        response.raise_for_status()
        data = response.json()
        results = data.get("items", [])

        _autocomplete_cache_set(cache_key, results)
        return results

    except (httpx.HTTPError, ValueError) as exc:
        print(
            f"⚠️ Google Books autocomplete indisponível: {exc}"
        )
        return []


def _normalize_authors(value: object) -> list[str]:
    """Normaliza autores retornados por APIs diferentes."""

    if not value:
        return []

    if isinstance(value, str):
        return [value.strip()] if value.strip() else []

    if isinstance(value, list):
        return [
            str(author).strip()
            for author in value
            if str(author).strip()
        ]

    return []


def _first_list_item(value: object) -> object | None:
    """Retorna o primeiro item de uma lista quando disponível."""

    if isinstance(value, list) and value:
        return value[0]

    return None


def _openlibrary_cover_url(
    cover_id: int | str | None,
) -> str | None:
    """Monta a URL da capa a partir do cover_i do Open Library."""

    if not cover_id:
        return None

    return (
        f"{OPENLIBRARY_COVERS_URL}/"
        f"{cover_id}-M.jpg?default=false"
    )


def _build_openlibrary_suggestion(
    doc: dict,
) -> dict | None:
    """
    Converte um Work do Open Library em candidato de autocomplete.

    Quando o Work não possui metadados suficientes, tenta usar a primeira
    Edition retornada pelo próprio Search API para enriquecer o candidato.
    """

    title = doc.get("title")
    work_key = doc.get("key")

    if not title or not work_key:
        return None

    work_authors = _normalize_authors(
        doc.get("author_name")
    )
    first_publish_year = doc.get("first_publish_year")
    cover_id = doc.get("cover_i")
    edition_count = doc.get("edition_count") or 0

    editions = doc.get("editions") or {}
    edition_docs = (
        editions.get("docs", [])
        if isinstance(editions, dict)
        else []
    )
    first_edition = (
        edition_docs[0]
        if edition_docs and isinstance(edition_docs[0], dict)
        else {}
    )

    edition_authors = _normalize_authors(
        first_edition.get("author_name")
    )
    authors = work_authors or edition_authors

    if not first_publish_year:
        publish_date = first_edition.get("publish_date")

        if publish_date:
            match = re.search(r"\b(\d{4})\b", str(publish_date))
            first_publish_year = (
                match.group(1)
                if match
                else None
            )

    if not cover_id:
        cover_id = first_edition.get("cover_i")

    edition_key = first_edition.get("key")
    edition_keys = doc.get("edition_key") or []

    source_id = (
        edition_key
        or _first_list_item(edition_keys)
        or str(work_key).replace("/works/", "")
    )

    return {
        "title": title,
        "subtitle": doc.get("subtitle"),
        "authors": authors,
        "author": authors[0] if authors else None,
        "year": (
            str(first_publish_year)
            if first_publish_year
            else None
        ),
        "thumbnail": _openlibrary_cover_url(cover_id),
        "source": "openlibrary",
        "source_id": str(source_id),
        "edition_count": edition_count,
    }


def _build_google_suggestion(
    item: dict,
) -> dict | None:
    """Converte um volume do Google Books em candidato de autocomplete."""

    volume_info = item.get("volumeInfo") or {}
    title = volume_info.get("title")

    if not title:
        return None

    authors = _normalize_authors(
        volume_info.get("authors")
    )
    image_links = volume_info.get("imageLinks") or {}

    thumbnail = (
        image_links.get("thumbnail")
        or image_links.get("smallThumbnail")
    )

    if thumbnail and thumbnail.startswith("http://"):
        thumbnail = "https://" + thumbnail[7:]

    return {
        "title": title,
        "subtitle": volume_info.get("subtitle"),
        "authors": authors,
        "author": authors[0] if authors else None,
        "year": (
            str(volume_info["publishedDate"])
            if volume_info.get("publishedDate")
            else None
        ),
        "thumbnail": thumbnail,
        "source": "google",
        "source_id": str(item.get("id") or ""),
        "page_count": volume_info.get("pageCount"),
        "publisher": volume_info.get("publisher"),
        "average_rating": volume_info.get("averageRating"),
        "ratings_count": volume_info.get("ratingsCount"),
    }


def _build_database_suggestion(
    book: Book,
) -> dict:
    """Converte um livro salvo no banco em uma sugestão de autocomplete."""

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
        "year": str(book.published_year) if book.published_year else None,
        "thumbnail": book.thumbnail,
        "source": "database",
        "source_id": str(book.id),
    }


def _autocomplete_quality_penalty(
    title: str,
    subtitle: str | None = None,
) -> float:
    """
    Penaliza materiais derivados sem penalizar subtítulos legítimos.

    Termos genéricos como "guide" ou "analysis" podem fazer parte do
    subtítulo oficial de uma obra legítima. Por isso, a penalização forte
    é aplicada principalmente ao título; no subtítulo usamos apenas
    expressões compostas claramente derivadas.
    """

    normalized_title = normalize_text(title)
    normalized_subtitle = normalize_text(subtitle)
    penalty = 0.0

    # No próprio título, estes termos são fortes indicadores de material
    # derivado/complementar para fins de autocomplete.
    for term in AUTOCOMPLETE_DERIVED_TERMS:
        normalized_term = normalize_text(term)

        if (
            normalized_term
            and normalized_term in normalized_title
        ):
            penalty += 24.0

    # No subtítulo, somente expressões compostas são consideradas.
    subtitle_derived_terms = {
        "study guide",
        "reading guide",
        "teacher guide",
        "teachers guide",
        "conversation starters",
        "workbook",
        "companion",
        "book analysis",
        "book summary",
        "análise do livro",
        "resumo do livro",
        "guia de estudo",
        "guia de leitura",
        "guia do professor",
    }

    for term in subtitle_derived_terms:
        normalized_term = normalize_text(term)

        if (
            normalized_term
            and normalized_term in normalized_subtitle
        ):
            penalty += 18.0

    subtitle_tokens = tokenize(subtitle)

    # Subtítulos gigantes podem indicar material SEO/cópia, mas a
    # penalização é leve para não eliminar edições legítimas.
    if len(subtitle_tokens) >= 16:
        penalty += min(
            (len(subtitle_tokens) - 15) * 1.0,
            6.0,
        )

    return min(penalty, 48.0)

def _is_strong_autocomplete_match(
    query: str,
    title: str,
    subtitle: str | None = None,
) -> bool:
    """Mantém somente títulos que correspondem ao prefixo digitado."""

    normalized_query = normalize_text(query)
    normalized_title = normalize_text(title)

    if not normalized_query or not normalized_title:
        return False

    combined = " ".join(
        value
        for value in (
            normalized_title,
            normalize_text(subtitle),
        )
        if value
    )

    for term in AUTOCOMPLETE_HARD_EXCLUDE_TERMS:
        normalized_term = normalize_text(term)

        if not normalized_term:
            continue

        pattern = rf"\b{re.escape(normalized_term)}\b"

        if re.search(pattern, combined):
            return False

    if normalized_title == normalized_query:
        return True

    if normalized_title.startswith(
        normalized_query + " "
    ):
        return True

    query_tokens = tokenize(normalized_query)
    title_tokens = tokenize(normalized_title)

    if (
        not query_tokens
        or not title_tokens
        or len(query_tokens) > len(title_tokens)
    ):
        return False

    return all(
        title_token.startswith(query_token)
        for query_token, title_token in zip(
            query_tokens,
            title_tokens,
        )
    )


def _autocomplete_text_score(
    query: str,
    title: str,
    subtitle: str | None = None,
) -> float:
    """Calcula a correspondência textual do candidato."""

    normalized_query = normalize_text(query)
    normalized_title = normalize_text(title)

    if not normalized_query or not normalized_title:
        return 0.0

    query_tokens = tokenize(normalized_query)
    title_tokens = tokenize(normalized_title)

    if normalized_title == normalized_query:
        score = 130.0
    elif normalized_title.startswith(
        normalized_query + " "
    ):
        score = 116.0
    elif normalized_title.startswith(
        normalized_query
    ):
        score = 108.0
    else:
        matched_tokens = 0

        for query_token, title_token in zip(
            query_tokens,
            title_tokens,
        ):
            if title_token.startswith(query_token):
                matched_tokens += 1
            else:
                break

        if (
            not query_tokens
            or matched_tokens != len(query_tokens)
        ):
            return 0.0

        score = 98.0

    extra_tokens = max(
        0,
        len(title_tokens) - len(query_tokens),
    )

    if extra_tokens:
        score -= min(
            extra_tokens * 2.5,
            18.0,
        )

    if subtitle:
        score += 1.5

    return round(
        max(0.0, min(score, 130.0)),
        2,
    )


def _autocomplete_author_key(
    author: str | None,
) -> str:
    """Cria uma chave estável para pequenas variações no nome do autor."""

    tokens = tokenize(author)

    if not tokens:
        return ""

    # Mantém o primeiro e o último nome; isso faz, por exemplo,
    # "Aditya Y Bhargava" e "Aditya Bhargava" representarem a mesma pessoa.
    if len(tokens) >= 2:
        return f"{tokens[0]} {tokens[-1]}"

    return tokens[0]


def _autocomplete_identity_key(
    suggestion: dict,
) -> tuple[str, str]:
    """
    Identidade usada para merge entre fontes.

    Título + autor é usado quando ambos existem. Se uma fonte não trouxe
    o autor, usamos apenas o título para permitir o enriquecimento posterior.
    """

    title = normalize_text(suggestion.get("title"))
    author_key = _autocomplete_author_key(
        suggestion.get("author")
    )

    return title, author_key


def _suggestion_completeness(
    suggestion: dict,
) -> int:
    """Mede a completude dos metadados exibidos no autocomplete."""

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


def _merge_suggestion_metadata(
    current: dict,
    incoming: dict,
) -> dict:
    """Combina metadados de dois candidatos da mesma identidade."""

    merged = dict(current)

    fields = (
        "subtitle",
        "year",
        "thumbnail",
        "author",
        "authors",
        "page_count",
        "publisher",
        "average_rating",
        "ratings_count",
        "edition_count",
    )

    for field in fields:
        current_value = merged.get(field)
        incoming_value = incoming.get(field)

        if not current_value and incoming_value:
            merged[field] = incoming_value

    # Quando os autores representam a mesma pessoa, o Google costuma
    # oferecer uma grafia bibliográfica mais consistente para exibição.
    if (
        merged.get("author")
        and incoming.get("author")
        and _autocomplete_author_key(merged.get("author"))
        == _autocomplete_author_key(incoming.get("author"))
        and incoming.get("source") == "google"
    ):
        merged["author"] = incoming["author"]
        merged["authors"] = incoming.get("authors") or merged.get("authors")

    # Se o candidato mais completo veio de outra fonte, usamos a capa dele.
    if (
        not merged.get("thumbnail")
        and incoming.get("thumbnail")
    ):
        merged["thumbnail"] = incoming["thumbnail"]

    return merged


def _autocomplete_source_bonus(
    suggestion: dict,
) -> float:
    """
    Bônus pequeno pela confiabilidade da fonte.

    O banco local é útil para velocidade, mas não deve superar uma fonte
    externa somente por ser local, porque pode conter dados antigos ou
    incorretos.
    """

    source = suggestion.get("source")

    return {
        "google": 6.0,
        "openlibrary": 5.0,
        "database": 1.0,
    }.get(source, 0.0)

def _autocomplete_candidate_score(
    query: str,
    suggestion: dict,
) -> float:
    """Score final de um candidato antes do merge."""

    score = _autocomplete_text_score(
        query,
        suggestion["title"],
        suggestion.get("subtitle"),
    )

    score -= _autocomplete_quality_penalty(
        suggestion["title"],
        suggestion.get("subtitle"),
    )

    score += _autocomplete_source_bonus(suggestion)
    score += _suggestion_completeness(suggestion) * 2.0

    try:
        edition_count = int(
            suggestion.get("edition_count") or 0
        )
    except (TypeError, ValueError):
        edition_count = 0

    # Popularidade no Open Library ajuda a desempatar, mas nunca domina
    # a correspondência do título.
    if edition_count > 1:
        score += min(
            edition_count / 25.0,
            4.0,
        )

    return round(max(score, 0.0), 2)


def _prepare_source_candidates(
    query: str,
    suggestions: list[dict],
) -> list[tuple[float, dict]]:
    """Filtra e pontua candidatos vindos de uma única fonte."""

    candidates: list[tuple[float, dict]] = []

    for suggestion in suggestions:
        title = suggestion.get("title")

        if not title:
            continue

        if not _is_strong_autocomplete_match(
            query,
            title,
            suggestion.get("subtitle"),
        ):
            continue

        score = _autocomplete_candidate_score(
            query,
            suggestion,
        )

        if score < 55.0:
            continue

        candidates.append((score, suggestion))

    return candidates


def suggest_books(
    query: str,
    db: Session,
    limit: int = AUTOCOMPLETE_MAX_RESULTS,
) -> list[dict]:
    """
    Retorna sugestões rápidas para o autocomplete.

    Pipeline:
        1. valida e verifica cache final;
        2. busca no banco por prefixo;
        3. consulta Open Library + Google Books em paralelo;
        4. filtra correspondência textual forte;
        5. faz merge por título + autor;
        6. completa metadados de uma fonte com outra;
        7. ranqueia e retorna até quatro candidatos.

    Gemini nunca é chamado e nenhum novo livro é salvo.
    """

    query = query.strip()

    if len(query) < 2:
        return []

    normalized_query = normalize_text(query)

    if not normalized_query:
        return []

    limit = max(
        1,
        min(limit, AUTOCOMPLETE_MAX_RESULTS),
    )

    final_cache_key = f"result:{normalized_query}"
    cached_final = _autocomplete_cache_get(final_cache_key)

    if cached_final is not None:
        return cached_final[:limit]  # type: ignore[index]

    merged: dict[tuple[str, str], tuple[float, dict]] = {}

    def add_candidate(
        score: float,
        suggestion: dict,
    ) -> None:
        key = _autocomplete_identity_key(suggestion)
        current = merged.get(key)

        if current is None:
            merged[key] = (score, suggestion)
            return

        current_score, current_suggestion = current
        combined = _merge_suggestion_metadata(
            current_suggestion,
            suggestion,
        )

        combined_score = max(
            current_score,
            score,
        )

        # Metadados vindos do segundo provedor podem transformar um
        # candidato inicialmente fraco em um resultado útil.
        combined_score += max(
            0,
            _suggestion_completeness(combined)
            - _suggestion_completeness(current_suggestion),
        ) * 1.5

        merged[key] = (
            round(combined_score, 2),
            combined,
        )

    # ========================================================
    # 1. BANCO LOCAL
    # ========================================================

    local_books = (
        db.query(Book)
        .filter(Book.title.ilike(f"{query}%"))
        .limit(12)
        .all()
    )

    local_suggestions = [
        _build_database_suggestion(book)
        for book in local_books
    ]

    for score, suggestion in _prepare_source_candidates(
        query,
        local_suggestions,
    ):
        add_candidate(
            score,
            suggestion,
        )

    # ========================================================
    # 2. FONTES EXTERNAS EM PARALELO
    # ========================================================

    print(
        f"🔎 Autocomplete: consultando Open Library + Google Books "
        f"para '{query}'..."
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        openlibrary_future = executor.submit(
            _openlibrary_autocomplete_request,
            query,
        )
        google_future = executor.submit(
            _google_books_autocomplete_request,
            query,
        )

        try:
            openlibrary_docs = openlibrary_future.result()
        except Exception as exc:
            print(
                f"⚠️ Falha no Open Library autocomplete: {exc}"
            )
            openlibrary_docs = []

        try:
            google_items = google_future.result()
        except Exception as exc:
            print(
                f"⚠️ Falha no Google Books autocomplete: {exc}"
            )
            google_items = []

    # ========================================================
    # 3. OPEN LIBRARY
    # ========================================================

    openlibrary_suggestions = [
        suggestion
        for doc in openlibrary_docs
        if (
            suggestion := _build_openlibrary_suggestion(doc)
        )
    ]

    for score, suggestion in _prepare_source_candidates(
        query,
        openlibrary_suggestions,
    ):
        add_candidate(
            score,
            suggestion,
        )

    # ========================================================
    # 4. GOOGLE BOOKS
    # ========================================================

    google_suggestions = [
        suggestion
        for item in google_items
        if (
            suggestion := _build_google_suggestion(item)
        )
    ]

    for score, suggestion in _prepare_source_candidates(
        query,
        google_suggestions,
    ):
        add_candidate(
            score,
            suggestion,
        )

    # ========================================================
    # 5. RANKING FINAL
    # ========================================================

    ranked = list(merged.values())

    def _final_sort_key(
        item: tuple[float, dict],
    ) -> tuple[int, float, int, int, str]:
        score, suggestion = item
        title = suggestion.get("title") or ""
        exact_title = (
            normalize_text(title) == normalized_query
        )

        # Um título exatamente igual ao que foi digitado sempre vem antes
        # de uma variante como "Second Edition". Isso evita que uma edição
        # relacionada, porém menos aderente, desloque o resultado exato.
        # Dentro do mesmo grupo, score e completude continuam decidindo.
        source = suggestion.get("source")
        source_priority = {
            "google": 3,
            "openlibrary": 2,
            "database": 1,
        }.get(source, 0)

        return (
            1 if exact_title else 0,
            score,
            _suggestion_completeness(suggestion),
            source_priority,
            suggestion.get("year") or "",
        )

    ranked.sort(
        key=_final_sort_key,
        reverse=True,
    )

    # Uma mesma representação bibliográfica pode aparecer em mais de uma
    # fonte com pequenas diferenças de autor. Para o autocomplete, títulos
    # iguais ocupam apenas uma posição; variantes reais do título continuam
    # separadas.
    best_by_title: dict[str, tuple[float, dict]] = {}

    for score, suggestion in ranked:
        title_key = normalize_text(
            suggestion.get("title")
        )

        current = best_by_title.get(title_key)

        if current is None:
            best_by_title[title_key] = (
                score,
                suggestion,
            )
            continue

        current_score, current_suggestion = current

        current_exact = (
            title_key == normalized_query
        )
        incoming_exact = (
            title_key == normalized_query
        )

        # Para títulos exatos, uma fonte externa deve prevalecer sobre o
        # banco quando a autoria divergir, pois isso evita mostrar uma obra
        # local potencialmente desatualizada como se fosse a correspondência
        # bibliográfica principal.
        current_source = current_suggestion.get("source")
        incoming_source = suggestion.get("source")

        current_external = current_source in {
            "google",
            "openlibrary",
        }
        incoming_external = incoming_source in {
            "google",
            "openlibrary",
        }

        author_conflict = (
            bool(current_suggestion.get("author"))
            and bool(suggestion.get("author"))
            and _autocomplete_author_key(
                current_suggestion.get("author")
            )
            != _autocomplete_author_key(
                suggestion.get("author")
            )
        )

        if (
            current_exact
            and incoming_exact
            and author_conflict
            and incoming_external
            and not current_external
        ):
            best_by_title[title_key] = (
                score,
                _merge_suggestion_metadata(
                    suggestion,
                    current_suggestion,
                ),
            )
            continue

        current_quality = (
            current_score,
            _suggestion_completeness(current_suggestion),
            1 if current_external else 0,
            1 if current_source == "google" else 0,
        )
        incoming_quality = (
            score,
            _suggestion_completeness(suggestion),
            1 if incoming_external else 0,
            1 if incoming_source == "google" else 0,
        )

        if incoming_quality > current_quality:
            best_by_title[title_key] = (
                score,
                _merge_suggestion_metadata(
                    suggestion,
                    current_suggestion,
                ),
            )
        else:
            best_by_title[title_key] = (
                current_score,
                _merge_suggestion_metadata(
                    current_suggestion,
                    suggestion,
                ),
            )

    ranked = list(best_by_title.values())
    ranked.sort(
        key=_final_sort_key,
        reverse=True,
    )

    result = [
        suggestion
        for _, suggestion in ranked[:limit]
    ]

    _autocomplete_cache_set(
        final_cache_key,
        result,
    )

    print(
        f"✅ Autocomplete: {len(result)} sugestões retornadas."
    )

    for index, suggestion in enumerate(
        result,
        start=1,
    ):
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
        # English
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

        # Portuguese
        "trilogia",
        "coleção",
        "kit",
        "guia",
        "análise",
        "resumo",
        "manual",
        "estudo",
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