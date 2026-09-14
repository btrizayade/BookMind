import re
import unicodedata
from dataclasses import dataclass


# ============================================================
# CONFIGURAÇÃO
# ============================================================

MIN_FUZZY_SCORE = 45

EXCLUDED_TITLE_TERMS = {
    "study guide",
    "study guides",
    "workbook",
    "workbooks",
    "teacher guide",
    "teachers guide",
    "student guide",
    "summary",
    "summaries",
    "analysis",
    "companion",
    "companions",
    "book club",
    "reading guide",
    "reading guides",
    "lesson plan",
    "lesson plans",
    "answer key",
    "solutions manual",
    "solutions",
    "annotated guide",
}

COLLECTION_TERMS = {
    "box set",
    "boxset",
    "boxed set",
    "complete collection",
    "complete works",
    "collected works",
    "collection",
    "anthology",
    "omnibus",
    "bundle",
    "trilogy",
    "series",
    "volume 1",
    "volume 2",
    "volume 3",
    "vol 1",
    "vol 2",
    "vol 3",
}


# ============================================================
# RESULTADO DO RANKING
# ============================================================

@dataclass(frozen=True)
class SearchRank:
    """
    Resultado intermediário usado para ordenar candidatos.
    """

    total_score: float
    title_score: float
    author_score: float
    quality_score: float
    penalties: float


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalize_text(value: str | None) -> str:
    """
    Normaliza texto para comparação.

    Exemplos:

        "Grokking Algorithms!"
        "grokking algorithms"

    tornam-se:

        "grokking algorithms"
    """

    if not value:
        return ""

    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower()

    value = re.sub(
        r"[^\w\s]",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def tokenize(value: str | None) -> list[str]:
    """
    Divide um texto normalizado em tokens.
    """

    normalized = normalize_text(value)

    if not normalized:
        return []

    return normalized.split()


# ============================================================
# TÍTULO
# ============================================================

def calculate_title_score(
    searched_title: str,
    result_title: str,
) -> float:
    """
    Calcula a relevância entre o título pesquisado e o título
    retornado.

    A pontuação considera:

    - título exatamente igual
    - resultado começando pela pesquisa
    - pesquisa começando pelo resultado
    - palavras da pesquisa presentes no resultado
    - ordem das palavras
    - proximidade textual
    - diferença de tamanho

    Importante:

    "Grokking Algorithms"
        ->
    "Grokking Algorithms An Illustrated Guide..."

    é uma extensão válida.

    Da mesma forma:

    "Grokking Algorithms An Illustrated"
        ->
    "Grokking Algorithms"

    é considerado um possível título-base válido,
    porém recebe uma pontuação menor do que um resultado
    que contém o título completo pesquisado.
    """

    searched = normalize_text(searched_title)
    result = normalize_text(result_title)

    if not searched or not result:
        return 0.0

    # --------------------------------------------------------
    # CORRESPONDÊNCIA EXATA
    # --------------------------------------------------------

    if searched == result:
        return 88.0

    searched_tokens = tokenize(searched)
    result_tokens = tokenize(result)

    if not searched_tokens or not result_tokens:
        return 0.0

    searched_token_set = set(searched_tokens)
    result_token_set = set(result_tokens)

    common_tokens = searched_token_set.intersection(
        result_token_set
    )

    token_overlap = (
        len(common_tokens)
        / len(searched_token_set)
    )

    score = token_overlap * 55.0

    # --------------------------------------------------------
    # RESULTADO É EXTENSÃO DA PESQUISA
    # --------------------------------------------------------
    #
    # Exemplo:
    #
    # pesquisa:
    # "grokking algorithms"
    #
    # resultado:
    # "grokking algorithms an illustrated guide"
    #
    # Isso é uma correspondência forte.
    # --------------------------------------------------------

    if result.startswith(searched):
        score += 35.0

    # --------------------------------------------------------
    # PESQUISA É EXTENSÃO DO RESULTADO
    # --------------------------------------------------------
    #
    # Exemplo:
    #
    # pesquisa:
    # "grokking algorithms an illustrated"
    #
    # resultado:
    # "grokking algorithms"
    #
    # Isso é potencialmente válido, mas menos preciso do que
    # encontrar exatamente o título completo pesquisado.
    # --------------------------------------------------------

    elif searched.startswith(result):
        result_ratio = (
            len(result_tokens)
            / len(searched_tokens)
        )

        # Base relativamente alta para não rejeitar
        # automaticamente o título-base.
        #
        # Quanto mais do título pesquisado o resultado cobre,
        # maior a pontuação.
        score = 65.0 + (result_ratio * 15.0)

    # --------------------------------------------------------
    # PRIMEIRAS PALAVRAS
    # --------------------------------------------------------

    if result_tokens[: len(searched_tokens)] == searched_tokens:
        score += 10.0

    # --------------------------------------------------------
    # ORDEM
    # --------------------------------------------------------

    search_position = 0
    ordered_matches = 0

    for token in searched_tokens:
        try:
            position = result_tokens.index(
                token,
                search_position,
            )
        except ValueError:
            continue

        ordered_matches += 1
        search_position = position + 1

    order_score = (
        ordered_matches
        / len(searched_tokens)
    )

    score += order_score * 10.0

    # --------------------------------------------------------
    # TAMANHO
    # --------------------------------------------------------
    #
    # Só aplicamos penalidade quando o resultado é MAIOR
    # que a pesquisa.
    #
    # Quando o resultado é menor, já tratamos essa situação
    # explicitamente como "título-base".
    # --------------------------------------------------------

    if len(result_tokens) > len(searched_tokens):
        extra_tokens = (
            len(result_tokens)
            - len(searched_tokens)
        )

        # Pequenas extensões são normais.
        #
        # "Grokking Algorithms"
        # ->
        # "Grokking Algorithms An Illustrated Guide..."
        #
        # Extensões muito grandes começam a perder relevância.

        size_penalty = min(
            extra_tokens * 2.0,
            18.0,
        )

        score -= size_penalty

    return round(
        max(0.0, min(score, 100.0)),
        2,
    )


# ============================================================
# AUTOR
# ============================================================

def calculate_author_score(
    searched_author: str | None,
    result_authors: list[str] | None,
) -> float:
    """
    Calcula compatibilidade entre o autor pesquisado e os
    autores retornados.
    """

    searched = normalize_text(searched_author)

    if not searched:
        return 0.0

    if not result_authors:
        return 0.0

    searched_tokens = set(
        tokenize(searched)
    )

    if not searched_tokens:
        return 0.0

    best_score = 0.0

    for author in result_authors:
        normalized_author = normalize_text(author)

        author_tokens = set(
            tokenize(normalized_author)
        )

        if not author_tokens:
            continue

        # Correspondência exata
        if normalized_author == searched:
            best_score = max(
                best_score,
                100.0,
            )
            continue

        common_tokens = (
            searched_tokens.intersection(
                author_tokens
            )
        )

        score = (
            len(common_tokens)
            / len(searched_tokens)
        ) * 100.0

        if normalized_author.startswith(searched):
            score += 15.0

        best_score = max(
            best_score,
            min(score, 100.0),
        )

    return round(
        best_score,
        2,
    )


# ============================================================
# QUALIDADE DO RESULTADO
# ============================================================

def calculate_quality_score(
    *,
    authors: list[str] | None = None,
    page_count: int | None = None,
    publisher: str | None = None,
    thumbnail: str | None = None,
    published_year: str | None = None,
) -> float:
    """
    Mede a qualidade dos metadados disponíveis.

    Isso não decide qual livro é correto.
    Serve apenas como critério secundário para desempate.
    """

    score = 0.0

    if authors:
        score += 25.0

    if page_count:
        score += 20.0

    if publisher:
        score += 15.0

    if thumbnail:
        score += 15.0

    if published_year:
        score += 15.0

    return min(score, 100.0)


# ============================================================
# PENALIDADES
# ============================================================

def calculate_title_penalty(
    result_title: str,
) -> float:
    """
    Penaliza resultados que parecem materiais
    complementares ou coleções em vez da obra principal.
    """

    normalized_title = normalize_text(
        result_title
    )

    if not normalized_title:
        return 0.0

    penalty = 0.0

    # --------------------------------------------------------
    # MATERIAL COMPLEMENTAR
    # --------------------------------------------------------

    for term in EXCLUDED_TITLE_TERMS:
        normalized_term = normalize_text(term)

        if normalized_term in normalized_title:
            penalty += 35.0

    # --------------------------------------------------------
    # COLEÇÕES
    # --------------------------------------------------------

    for term in COLLECTION_TERMS:
        normalized_term = normalize_text(term)

        if normalized_term in normalized_title:
            penalty += 45.0

    return min(
        penalty,
        80.0,
    )


# ============================================================
# RANKING FINAL
# ============================================================

def rank_book(
    *,
    searched_title: str,
    result_title: str,
    searched_author: str | None = None,
    result_authors: list[str] | None = None,
    page_count: int | None = None,
    publisher: str | None = None,
    thumbnail: str | None = None,
    published_year: str | None = None,
) -> SearchRank:
    """
    Calcula a relevância final de um resultado.

    Título é o principal sinal.

    Autor, qualidade dos metadados e penalidades funcionam
    como sinais complementares.
    """

    title_score = calculate_title_score(
        searched_title,
        result_title,
    )

    author_score = calculate_author_score(
        searched_author,
        result_authors,
    )

    quality_score = calculate_quality_score(
        authors=result_authors,
        page_count=page_count,
        publisher=publisher,
        thumbnail=thumbnail,
        published_year=published_year,
    )

    penalties = calculate_title_penalty(
        result_title
    )

    # --------------------------------------------------------
    # BUSCA COM AUTOR
    # --------------------------------------------------------

    if searched_author:
        total_score = (
            title_score * 0.65
            + author_score * 0.25
            + quality_score * 0.10
            - penalties
        )

    # --------------------------------------------------------
    # BUSCA APENAS POR TÍTULO
    # --------------------------------------------------------

    else:
        total_score = (
            title_score * 0.75
            + quality_score * 0.25
            - penalties
        )

    return SearchRank(
        total_score=round(
            max(0.0, total_score),
            2,
        ),
        title_score=round(
            title_score,
            2,
        ),
        author_score=round(
            author_score,
            2,
        ),
        quality_score=round(
            quality_score,
            2,
        ),
        penalties=round(
            penalties,
            2,
        ),
    )


# ============================================================
# VALIDAÇÃO MÍNIMA
# ============================================================

def is_viable_result(
    searched_title: str,
    result_title: str,
) -> bool:
    """
    Decide se um resultado possui correspondência mínima
    suficiente para continuar no ranking.

    Resultados que são um título-base do texto pesquisado
    continuam viáveis, mas recebem uma pontuação menor
    no ranking final do que uma correspondência completa.
    """

    score = calculate_title_score(
        searched_title,
        result_title,
    )

    return score >= MIN_FUZZY_SCORE