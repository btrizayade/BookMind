import re
import unicodedata

import httpx


BASE_URL = "https://openlibrary.org/search.json"


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def _normalize_text(text: str | None) -> str:
    """
    Normaliza texto para facilitar comparações.
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
# AUTOR
# ============================================================

def _author_matches(
    searched_author: str | None,
    authors: list[str],
) -> bool:
    """
    Verifica se algum autor retornado pelo Open Library
    corresponde ao autor pesquisado.
    """

    if not searched_author or not authors:
        return False

    searched = _normalize_text(
        searched_author
    )

    searched_parts = set(
        searched.split()
    )

    for author in authors:

        normalized_author = _normalize_text(
            author
        )

        # Correspondência exata
        if normalized_author == searched:
            return True

        result_parts = set(
            normalized_author.split()
        )

        # Alguma parte relevante em comum
        if (
            searched_parts
            and searched_parts.intersection(
                result_parts
            )
        ):
            return True

    return False


# ============================================================
# SCORE DO TÍTULO
# ============================================================

def _calculate_title_score(
    searched_title: str,
    result_title: str,
) -> int:
    """
    Calcula a compatibilidade entre dois títulos.
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
# BUSCA OPEN LIBRARY
# ============================================================

def search_book_metadata(
    title: str,
    author: str | None = None,
) -> dict | None:
    """
    Busca metadados de um livro no Open Library.

    Retorna:

        {
            "title": str | None,
            "authors": list[str],
            "page_count": int | None,
            "published_year": str | None,
        }

    O objetivo principal é completar dados que estejam
    ausentes no Google Books.
    """

    params = {
        "title": title,
        "limit": 10,
        "fields": (
            "title,"
            "author_name,"
            "number_of_pages_median,"
            "first_publish_year"
        ),
    }

    try:
        response = httpx.get(
            BASE_URL,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

    except Exception as exc:
        print(
            f"⚠️ Open Library indisponível: {exc}"
        )
        return None

    docs = data.get(
        "docs",
        [],
    )

    if not docs:
        print(
            "⚠️ Nenhum resultado encontrado "
            "no Open Library."
        )
        return None

    normalized_title = _normalize_text(
        title
    )

    candidates = []

    for doc in docs:

        result_title = doc.get(
            "title"
        )

        if not result_title:
            continue

        normalized_result_title = (
            _normalize_text(
                result_title
            )
        )

        title_score = _calculate_title_score(
            normalized_title,
            normalized_result_title,
        )

        # Ignora títulos muito diferentes
        if title_score < 50:
            continue

        authors = doc.get(
            "author_name",
            [],
        )

        author_match = _author_matches(
            author,
            authors,
        )

        page_count = doc.get(
            "number_of_pages_median"
        )

        candidates.append(
            (
                author_match,
                title_score,
                bool(page_count),
                doc,
            )
        )

    if not candidates:
        print(
            "⚠️ Nenhum resultado adequado encontrado "
            "no Open Library."
        )
        return None

    # Prioridade:
    # 1. autor compatível
    # 2. título mais parecido
    # 3. presença de número de páginas
    candidates.sort(
        key=lambda candidate: (
            candidate[0],
            candidate[1],
            candidate[2],
        ),
        reverse=True,
    )

    best_doc = candidates[0][3]

    result_authors = best_doc.get(
        "author_name",
        [],
    )

    result_pages = best_doc.get(
        "number_of_pages_median"
    )

    result_year = best_doc.get(
        "first_publish_year"
    )

    print(
        f"📚 Open Library encontrou: "
        f"{best_doc.get('title')}"
    )

    if result_authors:
        print(
            "   👤 Autor: "
            + ", ".join(result_authors)
        )

    if result_pages:
        print(
            f"   📄 Páginas: {result_pages}"
        )

    if result_year:
        print(
            f"   📅 Primeiro ano de publicação: "
            f"{result_year}"
        )

    return {
        "title": best_doc.get("title"),
        "authors": result_authors,
        "page_count": result_pages,
        "published_year": (
            str(result_year)
            if result_year
            else None
        ),
    }