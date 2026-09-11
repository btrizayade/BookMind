import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.book import BookResponse
from app.schemas.recommendation import RecommendationRequest


load_dotenv()


# ============================================================
# GEMINI CLIENT
# ============================================================

MODEL_NAME = "gemini-3.5-flash"

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        timeout=60000,
        retry_options=types.HttpRetryOptions(
            attempts=2,
            initial_delay=1,
            max_delay=10,
            http_status_codes=[503, 504],
        ),
    ),
)


# ============================================================
# CONSTANTES
# ============================================================

GENRE_TERMS = {
    "romance": "romance",
    "fantasy_romantasy": "fantasy or romantasy",
    "thriller_mystery_crime": "thriller, mystery, or crime",
    "science_fiction": "science fiction",
    "horror": "horror",
    "personal_development_nonfiction": (
        "personal development or nonfiction"
    ),
    "young_adult": "young adult",
}


LOOKING_FOR_TERMS = {
    "emotional": "emotional",
    "mysterious": "mysterious",
    "easy_to_read": "easy to read",
    "tearjerker": "emotionally moving",
    "short_book": "short",
    "dark": "dark",
    "intellectually_challenging": (
        "intellectually challenging"
    ),
}


MOOD_TERMS = {
    "relaxing": "relaxing",
    "emotional": "emotional",
    "thought_provoking": "thought-provoking",
    "dark": "dark",
    "wholesome": "wholesome",
}


EXPECTED_GENRES = {
    "romance",
    "fantasy_romantasy",
    "thriller_mystery_crime",
    "science_fiction",
    "horror",
    "personal_development_nonfiction",
    "young_adult",
}


EXPECTED_READING_PROFILE = {
    "emotional",
    "mysterious",
    "easy_to_read",
    "tearjerker",
    "dark",
    "intellectually_challenging",
    "relaxing",
    "thought_provoking",
    "wholesome",
}


# ============================================================
# PYDANTIC INTERNAL MODELS
# ============================================================

class BookDNA(BaseModel):
    model_config = ConfigDict(extra="forbid")

    romance: int = Field(ge=0, le=100)
    fantasy_romantasy: int = Field(ge=0, le=100)
    thriller_mystery_crime: int = Field(ge=0, le=100)
    science_fiction: int = Field(ge=0, le=100)
    horror: int = Field(ge=0, le=100)
    personal_development_nonfiction: int = Field(
        ge=0,
        le=100,
    )
    young_adult: int = Field(ge=0, le=100)


class ReadingProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emotional: int = Field(ge=0, le=100)
    mysterious: int = Field(ge=0, le=100)
    easy_to_read: int = Field(ge=0, le=100)
    tearjerker: int = Field(ge=0, le=100)
    dark: int = Field(ge=0, le=100)
    intellectually_challenging: int = Field(
        ge=0,
        le=100,
    )
    relaxing: int = Field(ge=0, le=100)
    thought_provoking: int = Field(ge=0, le=100)
    wholesome: int = Field(ge=0, le=100)


class BookAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    book_dna: BookDNA
    reading_profile: ReadingProfile
    themes: list[str]
    atmosphere: list[str]
    story_elements: list[str]

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        value = value.strip()

        words = value.split()

        if not 35 <= len(words) <= 60:
            raise ValueError(
                "Summary must contain between 35 and 60 words."
            )

        forbidden_terms = {
            "experience",
            "learn",
            "discover",
            "enjoy",
            "gain",
        }

        lowered = value.lower()

        for term in forbidden_terms:
            if re.search(
                rf"\b{re.escape(term)}\b",
                lowered,
            ):
                raise ValueError(
                    f"Summary contains forbidden term: {term}"
                )

        return value

@field_validator(
    "themes",
    "atmosphere",
    "story_elements",
)
@classmethod
def validate_lists(
    cls,
    values: list[str],
) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("Value must be a list.")

    cleaned = []

    for item in values:
        if not isinstance(item, str):
            continue

        item = item.strip()

        if not item:
            continue

        # Mantém os itens curtos sem invalidar
        # toda a análise caso o Gemini ultrapasse
        # ligeiramente o limite.
        words = item.split()

        if len(item.split()) > 8:
            raise ValueError(
                "List items must contain at most 8 words."
    )

        normalized = item.lower()

        if normalized not in {
            existing.lower()
            for existing in cleaned
        }:
            cleaned.append(item)

    return cleaned


# ============================================================
# FALLBACK HELPERS
# ============================================================

def _short_book_score(
    page_count: int | None,
) -> int:
    """
    Calcula objetivamente se o livro é curto.

    Menos de 200 páginas -> 100
    200 páginas ou mais -> 0
    """
    if page_count is None:
        return 0

    return 100 if page_count < 200 else 0


def _get_supported_preferences(
    book: BookResponse,
    preferences: RecommendationRequest,
) -> list[str]:
    """
    Retorna apenas as preferências do usuário que são
    realmente sustentadas pelo Reading Profile do livro.
    """
    profile = book.reading_profile or {}

    supported = []

    for preference in preferences.looking_for:
        if preference == "short_book":
            if (
                book.page_count is not None
                and book.page_count < 200
            ):
                supported.append(preference)

            continue

        score = profile.get(
            preference,
            0,
        )

        if score >= 50:
            supported.append(preference)

    mood_score = profile.get(
        preferences.mood,
        0,
    )

    if (
        mood_score >= 50
        and preferences.mood
        not in preferences.looking_for
    ):
        supported.append(
            f"mood:{preferences.mood}"
        )

    return supported


def _get_supported_genres(
    book: BookResponse,
    preferences: RecommendationRequest,
) -> list[str]:
    """
    Retorna somente os gêneros selecionados pelo usuário
    cuja pontuação no Book DNA seja >= 50.
    """
    book_dna = book.book_dna or {}

    supported = []

    for genre in preferences.genres:
        if book_dna.get(genre, 0) >= 50:
            supported.append(genre)

    return supported


def get_allowed_genres(
    book_dna: dict | None,
) -> tuple[list[str], list[str]]:
    """
    Divide os gêneros entre permitidos e proibidos.

    >= 50 -> permitido
    < 50 -> proibido
    """
    book_dna = book_dna or {}

    allowed_genres = [
        genre
        for genre, score in book_dna.items()
        if (
            isinstance(score, (int, float))
            and score >= 50
        )
    ]

    forbidden_genres = [
        genre
        for genre, score in book_dna.items()
        if (
            isinstance(score, (int, float))
            and score < 50
        )
    ]

    return (
        allowed_genres,
        forbidden_genres,
    )


def validate_recommendation_reason(
    reason: str,
) -> bool:
    """
    Valida formato básico da razão gerada pela IA.
    """
    if not isinstance(reason, str):
        return False

    reason = reason.strip()

    if not reason:
        return False

    if len(reason.split()) > 25:
        return False

    sentence_count = len(
        re.findall(
            r"[.!?]+",
            reason,
        )
    )

    if sentence_count != 1:
        return False

    lowered = reason.lower()

    forbidden_phrases = [
        "great choice",
        "you will love",
        "classic",
    ]

    for phrase in forbidden_phrases:
        if phrase in lowered:
            return False

    return True


def generate_fallback_reason(
    book: BookResponse,
    preferences: RecommendationRequest,
) -> str:
    """
    Gera uma razão local simples quando o Gemini não
    consegue responder.
    """
    profile = book.reading_profile or {}

    supported_preferences = []

    for preference in preferences.looking_for:
        if preference == "short_book":
            if (
                book.page_count is not None
                and book.page_count < 200
            ):
                supported_preferences.append(
                    "short"
                )

            continue

        if profile.get(preference, 0) >= 50:
            supported_preferences.append(
                LOOKING_FOR_TERMS.get(
                    preference,
                    preference,
                )
            )

    if profile.get(preferences.mood, 0) >= 50:
        supported_preferences.append(
            MOOD_TERMS.get(
                preferences.mood,
                preferences.mood,
            )
        )

    if not supported_preferences:
        return (
            "Its themes and reading experience offer "
            "a thoughtful match for readers with similar preferences."
        )

    unique_preferences = []

    for item in supported_preferences:
        if item not in unique_preferences:
            unique_preferences.append(item)

    if len(unique_preferences) >= 2:
        first = unique_preferences[0]
        second = unique_preferences[1]

        return (
            f"Its {first} and {second} qualities "
            "align with this reading experience."
        )

    first = unique_preferences[0]

    return (
        f"Its {first} qualities "
        "align well with this reading experience."
    )


def _fallback_reason_map(
    books: list[BookResponse],
    preferences: RecommendationRequest,
) -> dict[str, str]:
    return {
        book.title: generate_fallback_reason(
            book,
            preferences,
        )
        for book in books
    }


# ============================================================
# BOOK ANALYSIS
# ============================================================

def generate_book_analysis(
    book: BookResponse,
    subjects: list[str] | None = None,
) -> dict | None:
    """
    Gera a análise semântica completa de um livro.

    Retorna:
    - summary
    - book_dna
    - reading_profile
    - themes
    - atmosphere
    - story_elements

    short_book NÃO é gerado pelo Gemini.
    Ele é calculado posteriormente a partir do número de páginas.
    """
    subjects = subjects or []

    subjects_text = (
        ", ".join(subjects)
        if subjects
        else "None available"
    )

    prompt = f"""
You are an expert literary analyst.

Analyze the literary work below and return JSON only.

IMPORTANT:
You are analyzing the ORIGINAL LITERARY WORK itself,
not the specific edition being described.

The analysis must represent the core work written by
the stated author.

IGNORE edition-specific supplementary material, including:
- introductions
- forewords
- afterwords
- editor's notes
- critical essays
- commentary
- study guides
- annotations
- letters
- diary extracts
- appendices
- discussion questions
- publisher material
- other bonus content

Do NOT treat supplementary material as part of:
- the plot
- the themes
- the atmosphere
- the story elements
- the genre
- the reading experience

For the summary, describe only the original literary work.

For story_elements, include only elements that belong to
the original work's story.

For example, if an edition contains letters, essays,
or critical commentary after the original work, those
materials MUST NOT appear in story_elements or themes.

BOOK INFORMATION

Title:
{book.title}

Authors:
{", ".join(book.authors)}

Publisher:
{book.publisher or "Unknown"}

Categories:
{", ".join(book.categories) if book.categories else "Unknown"}

Language:
{book.language or "Unknown"}

Pages:
{book.page_count if book.page_count is not None else "Unknown"}

Description:
{book.description or "No description available."}


OPEN LIBRARY SUBJECTS

These subjects come from Open Library and may contain
broad, noisy, incomplete, or edition-specific classifications.

Use them ONLY as supporting context.

Do NOT blindly accept them as correct genre classifications.

Use your own judgment together with:
- title
- author
- description
- categories
- known characteristics of the literary work

Subjects:
{subjects_text}


BOOK DNA

Evaluate how strongly the original work belongs to each
of the following categories.

Categories:

1. romance
A romantic love relationship is central to the work.

2. fantasy_romantasy
The work contains substantial fantasy, magical,
mythological, or supernatural worldbuilding.

3. thriller_mystery_crime
Investigation, crime, suspense, danger, secrets,
or solving a mystery is a major driver of the work.

4. science_fiction
Science, technology, futuristic concepts, or speculative
science are substantial elements of the work.

5. horror
Fear, dread, terror, disturbing imagery, supernatural
threats, or horror conventions are central or strongly
present.

6. personal_development_nonfiction
The work is primarily nonfiction focused on self-help,
personal growth, development, or related subjects.

7. young_adult
The work is primarily intended for a young adult audience
and/or is clearly classified as YA.

BOOK DNA SCORING

Score each category from 0 to 100.

0-24:
Absent or negligible.

25-49:
Secondary presence.

50-74:
Strong presence.

75-100:
Central and defining characteristic.

IMPORTANT BOOK DNA RULES

- Judge every category independently.
- Do not inflate scores.
- Do not assign a high score merely because a term appears
  in the description or Open Library subjects.
- Consider the actual nature of the original work.
- Romance means romantic love is central, not merely present.
- Fantasy requires substantial speculative or magical elements.
- Thriller, mystery, or crime requires those elements to be
  major drivers of the work.
- Science fiction requires meaningful science, technology,
  futuristic, or speculative-science elements.
- Horror requires genuine horror characteristics.
- Dark or disturbing does NOT automatically mean horror.
- Young Adult refers to the work's intended audience,
  not simply the age of a character.
- Fiction should generally score very low on
  personal_development_nonfiction.


READING PROFILE

Rate the reading experience itself.

Score each characteristic from 0 to 100.

1. emotional
2. mysterious
3. easy_to_read
4. tearjerker
5. dark
6. intellectually_challenging
7. relaxing
8. thought_provoking
9. wholesome


READING PROFILE DEFINITIONS

emotional:
How strongly the work is likely to evoke emotions such as
love, sadness, empathy, or emotional attachment.

mysterious:
How strongly the work creates curiosity, unanswered
questions, secrets, or a sense of mystery.

easy_to_read:
How accessible the work is in terms of language,
narrative structure, and reading difficulty.

tearjerker:
How strongly the work is likely to provoke sadness,
emotional distress, or tears.

dark:
How strongly the work contains dark themes, atmosphere,
subject matter, or disturbing elements.

intellectually_challenging:
How strongly the work challenges the reader through
complex ideas, themes, structure, or interpretation.

relaxing:
How calm, comforting, gentle, or low-intensity the
overall reading experience is.

thought_provoking:
How strongly the work encourages reflection,
interpretation, or deeper consideration of ideas.

wholesome:
How strongly the work contains warmth, kindness,
comfort, optimism, hope, or uplifting elements.


IMPORTANT READING PROFILE RULES

- Judge every characteristic independently.
- Rate the actual reading experience.
- Do not infer characteristics from genre alone.
- Dark does not automatically mean horror.
- Mysterious does not automatically mean thriller or mystery.
- Emotional does not automatically mean romance.
- A book can score highly in multiple characteristics.
- Do not give high scores to weakly supported characteristics.


THEMES

Return 3 to 6 concrete themes from the original work.

Themes must describe substantive ideas or concepts in the
work, not genres.

Good examples:
- isolation
- identity
- grief
- social inequality
- family conflict

Avoid vague adjectives and generic statements.


ATMOSPHERE

Return 2 to 5 concise descriptors describing the atmosphere
of the original work.

Do not use genre names.

Good examples:
- claustrophobic
- melancholic
- tense
- surreal
- hopeful


STORY ELEMENTS

Return 2 to 5 concise non-spoiler elements.
Each element should normally contain 1 to 5 words.
Never exceed 8 words.

These must belong to the actual story.

Do NOT include:
- editor's notes
- critical essays
- letters
- diary extracts
- study questions
- publication information
- supplementary material


SUMMARY

Write one objective paragraph of 35 to 60 words.

The summary must describe the original literary work,
not the edition.

It should mention the central premise, conflict,
themes, or narrative characteristics.

Do not write marketing copy.

Do not directly address the reader.

Do not use:
- experience
- learn
- discover
- enjoy
- gain

Do not reveal major plot twists or the ending.


RETURN FORMAT

Return ONLY valid JSON.

Do not use Markdown.
Do not add explanations outside the JSON.
Do not add extra fields.

Use exactly this structure:

{{
    "summary": "35 to 60 word objective summary",
    "book_dna": {{
        "romance": 0,
        "fantasy_romantasy": 0,
        "thriller_mystery_crime": 0,
        "science_fiction": 0,
        "horror": 0,
        "personal_development_nonfiction": 0,
        "young_adult": 0
    }},
    "reading_profile": {{
        "emotional": 0,
        "mysterious": 0,
        "easy_to_read": 0,
        "tearjerker": 0,
        "dark": 0,
        "intellectually_challenging": 0,
        "relaxing": 0,
        "thought_provoking": 0,
        "wholesome": 0
    }},
    "themes": [
        "theme 1",
        "theme 2",
        "theme 3"
    ],
    "atmosphere": [
        "descriptor 1",
        "descriptor 2"
    ],
    "story_elements": [
        "element 1",
        "element 2"
    ]
}}
""".strip()

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        if not response.text:
            print(
                "⚠️ Gemini returned no book analysis."
            )
            return None

        raw_text = response.text.strip()

        result = json.loads(raw_text)

        analysis = BookAnalysis.model_validate(
            result
        )

        parsed = analysis.model_dump()

        # short_book is objective and derived locally.
        parsed["reading_profile"][
            "short_book"
        ] = _short_book_score(
            book.page_count
        )

        return parsed

    except Exception as exc:
        print(
            f"⚠️ Gemini book analysis failed: {exc}"
        )
        return None


# ============================================================
# RECOMMENDATION REASONS
# ============================================================

def _build_reason_prompt(
    books: list[BookResponse],
    preferences: RecommendationRequest,
) -> str:
    books_information = []

    for index, book in enumerate(
        books,
        start=1,
    ):
        allowed_genres, forbidden_genres = (
            get_allowed_genres(
                book.book_dna
            )
        )

        supported_preferences = (
            _get_supported_preferences(
                book,
                preferences,
            )
        )

        supported_genres = (
            _get_supported_genres(
                book,
                preferences,
            )
        )

        books_information.append(
            f"""
BOOK {index}

Title:
{book.title}

Authors:
{", ".join(book.authors)}

Book DNA:
{json.dumps(
    book.book_dna or {},
    ensure_ascii=False,
)}

Allowed Genres:
{", ".join(allowed_genres) if allowed_genres else "None"}

Forbidden Genres:
{", ".join(forbidden_genres) if forbidden_genres else "None"}

Reading Profile:
{json.dumps(
    book.reading_profile or {},
    ensure_ascii=False,
)}

Themes:
{", ".join(book.themes or []) or "None"}

Atmosphere:
{", ".join(book.atmosphere or []) or "None"}

Story Elements:
{", ".join(book.story_elements or []) or "None"}

Summary:
{book.ai_summary or "Not available"}

Supported User Preferences:
{", ".join(supported_preferences) if supported_preferences else "None"}

Supported Selected Genres:
{", ".join(supported_genres) if supported_genres else "None"}
""".strip()
        )

    books_text = "\n\n".join(
        books_information
    )

    return f"""
You are a personalized book recommendation assistant.

Generate exactly one concise personalized reason for
each provided book.

The reason must explain WHY that specific book fits
the particular reader.


USER PREFERENCES

Genres:
{", ".join(preferences.genres)}

Looking For:
{
    ", ".join(preferences.looking_for)
    if preferences.looking_for
    else "None"
}

Mood:
{preferences.mood}

Page Range:
{preferences.page_range}


BOOKS

{books_text}


HOW TO GENERATE THE REASONS

For each book:

1. Identify the strongest characteristics that match
   the user's preferences.

2. Use Book DNA to identify legitimate genre compatibility.

3. Use Reading Profile for the reading-experience match.

4. Use themes, atmosphere, and story elements to make
   the reason specific to that book.

5. Mention only characteristics that are meaningfully
   supported by the supplied data.

6. Prefer one or two strong matches rather than listing
   every compatible characteristic.

7. Focus on WHY this particular book fits this reader,
   not on describing the book generally.

8. Make reasons naturally varied.


GENRE ACCURACY RULES

- The Allowed Genres list is authoritative.
- A genre may be mentioned ONLY if it appears in
  Allowed Genres.
- Never mention a genre from Forbidden Genres.
- A genre with a Book DNA score below 50 is forbidden.
- Never infer genre from atmosphere or reading profile.
- Darkness does not imply horror.
- Mysterious does not imply thriller or mystery.
- Emotional does not imply romance.
- Supernatural, gothic, tragic, or disturbing elements
  do not automatically imply horror or fantasy.
- When uncertain, do not mention the genre.


IMPORTANT RULES

- Write in English.
- Maximum 25 words per reason.
- Exactly one sentence per reason.
- Do not summarize the plot.
- Do not mention compatibility scores.
- Do not mention pages or page range.
- Do not mention that the user selected specific options.
- Do not simply repeat the user's preferences.
- Never call the book a "classic".
- Never say "great choice".
- Never say "you will love this book".
- Never invent themes, atmosphere, genres, or preferences.
- Never describe a characteristic as strong when its score
  is low.
- Make the reason specific to the book.
- Return exactly one reason for every provided book.
- Return no additional books.


OUTPUT

Return ONLY valid JSON in exactly this format:

{{
    "reasons": [
        {{
            "title": "Exact book title",
            "reason": "One concise personalized sentence."
        }}
    ]
}}
""".strip()


def generate_recommendation_reasons(
    books: list[BookResponse],
    preferences: RecommendationRequest,
) -> dict[str, str]:
    """
    Gera as razões de recomendação em uma única chamada
    ao Gemini e aplica fallback local em caso de erro.
    """
    if not books:
        return {}

    fallback = _fallback_reason_map(
        books,
        preferences,
    )

    prompt = _build_reason_prompt(
        books,
        preferences,
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        if not response.text:
            print(
                "⚠️ Gemini returned no recommendation reasons."
            )
            return fallback

        raw_text = response.text.strip()

        result = json.loads(raw_text)

        reasons = {}

        items = result.get(
            "reasons",
            [],
        )

        if not isinstance(items, list):
            print(
                "⚠️ Gemini returned invalid recommendation format."
            )
            return fallback

        for item in items:
            if not isinstance(item, dict):
                continue

            title = item.get("title")
            reason = item.get("reason")

            if not isinstance(title, str):
                continue

            if not isinstance(reason, str):
                continue

            if title not in {
                book.title
                for book in books
            }:
                continue

            if validate_recommendation_reason(
                reason
            ):
                reasons[title] = reason.strip()

        for book in books:
            if book.title not in reasons:
                reasons[book.title] = fallback[
                    book.title
                ]

        return reasons

    except Exception as exc:
        print(
            "⚠️ Gemini batch recommendation reasons failed: "
            f"{exc}"
        )

        return fallback