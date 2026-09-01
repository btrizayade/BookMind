import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.schemas.book import BookResponse
from app.schemas.recommendation import RecommendationRequest


load_dotenv()


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        timeout=20000,
        retry_options=types.HttpRetryOptions(
            attempts=3,
            initial_delay=1,
            max_delay=10,
            http_status_codes=[503, 504],
        ),
    ),
)


def generate_book_analysis(book: BookResponse) -> dict | None:
    prompt = f"""
You are an expert book reviewer and literary analyst.

Analyze the book below and return three things:

1. A concise explanation of why someone should read it.
2. A Book DNA representing how strongly the book belongs to each genre category.
3. A Reading Profile representing the characteristics of the reading experience.

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
{book.page_count or "Unknown"}

Description:
{book.description or "No description available."}


BOOK DNA

Evaluate how strongly the book belongs to each of these seven categories.

1. romance
2. fantasy_romantasy
3. thriller_mystery_crime
4. science_fiction
5. horror
6. personal_development_nonfiction
7. young_adult


BOOK DNA SCORING

Score each category from 0 to 100.

0-10:
Almost completely absent.

11-30:
Minor presence.

31-50:
Secondary element.

51-70:
Relevant element.

71-90:
Major or dominant element.

91-100:
One of the defining characteristics of the book.


BOOK DNA IMPORTANT RULES

- Judge each category independently.
- A book can score highly in multiple categories.
- Do not assign a high score simply because a category appears in the description.
- Consider the actual nature, themes and genre of the book.
- Do not assume that "romance" means the book is a romantic novel.
- Young Adult refers to the target audience, not simply the age of the characters.
- Personal Development & Nonfiction should score very low for fictional works.
- Fantasy & Romantasy should score based on actual fantasy elements, not simply romance.
- Horror should reflect genuine horror or horror-related elements, not simply darkness or tragedy.


READING PROFILE

Evaluate the following characteristics of the book's reading experience.

Score each characteristic independently from 0 to 100.

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
How strongly the book is likely to evoke emotions such as love, sadness, empathy or emotional attachment.

mysterious:
How strongly the book creates curiosity, unanswered questions, secrets or a sense of mystery.

easy_to_read:
How accessible the book is in terms of language, narrative structure and overall reading difficulty.

tearjerker:
How strongly the book is likely to provoke sadness, emotional distress or tears.

dark:
How strongly the book contains dark themes, atmosphere, subject matter or disturbing elements.

intellectually_challenging:
How strongly the book challenges the reader through complex ideas, themes, structure or interpretation.

relaxing:
How calm, comforting, gentle or low-intensity the overall reading experience is.

thought_provoking:
How strongly the book encourages reflection, interpretation or deeper consideration of ideas and themes.

wholesome:
How strongly the book contains warmth, kindness, comfort, optimism, hope or uplifting elements.


READING PROFILE IMPORTANT RULES

- Judge each characteristic independently.
- Base the scores on the actual themes, tone, narrative style and reading experience of the book.
- Do not assume a characteristic is present simply because the book belongs to a related genre.
- A book can score highly in multiple characteristics.
- "easy_to_read" refers to reading accessibility, not whether the story is simple or lacking depth.
- "tearjerker" refers specifically to the likelihood of provoking tears or strong sadness.
- "dark" refers to dark themes, atmosphere or subject matter.
- "intellectually_challenging" refers to complexity of ideas, themes, structure or interpretation.
- "relaxing" refers to the overall emotional intensity and comfort of the reading experience.
- "thought_provoking" refers to the extent to which the book encourages reflection or deeper thinking.
- "wholesome" refers to warmth, kindness, comfort, optimism or uplifting elements.
- Do not give high scores to characteristics that are only weakly supported by the book.


SUMMARY RULES

- Write the summary in English.
- Return EXACTLY five bullet points.
- Start every bullet with "•".
- Maximum 15 words per bullet.
- Focus on what the reader will learn, experience or gain.
- Do not reveal major plot twists or endings.
- Return exactly five bullets.


RETURN FORMAT

Return ONLY valid JSON.

Do not use Markdown.
Do not add explanations outside the JSON.
Do not add extra fields.

Use exactly the structure below:

{{
    "summary": "• First point\\n• Second point\\n• Third point\\n• Fourth point\\n• Fifth point",
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
    }}
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )

        if not response.text:
            return None

        result = json.loads(response.text)

        if (
            "summary" not in result
            or "book_dna" not in result
            or "reading_profile" not in result
        ):
            print("⚠️ Gemini returned an incomplete response.")
            return None

        book_dna = result["book_dna"]

        expected_categories = {
            "romance",
            "fantasy_romantasy",
            "thriller_mystery_crime",
            "science_fiction",
            "horror",
            "personal_development_nonfiction",
            "young_adult",
        }

        if set(book_dna.keys()) != expected_categories:
            print("⚠️ Gemini returned invalid Book DNA categories.")
            return None

        for category, score in book_dna.items():
            if not isinstance(score, int) or not 0 <= score <= 100:
                print(
                    f"⚠️ Invalid Book DNA score for {category}: {score}"
                )
                return None

        reading_profile = result["reading_profile"]

        expected_reading_profile = {
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

        if set(reading_profile.keys()) != expected_reading_profile:
            print(
                "⚠️ Gemini returned invalid Reading Profile characteristics."
            )
            return None

        for characteristic, score in reading_profile.items():
            if not isinstance(score, int) or not 0 <= score <= 100:
                print(
                    f"⚠️ Invalid Reading Profile score "
                    f"for {characteristic}: {score}"
                )
                return None

        return {
            "summary": result["summary"],
            "book_dna": book_dna,
            "reading_profile": reading_profile,
        }

    except Exception as error:
        print(f"⚠️ Gemini unavailable: {error}")
        return None


def get_allowed_genres(
    book_dna: dict | None,
) -> tuple[list[str], list[str]]:
    """Split Book DNA into allowed (>=50) and forbidden (<50) genres."""
    book_dna = book_dna or {}

    allowed_genres = [
        genre
        for genre, score in book_dna.items()
        if isinstance(score, (int, float)) and score >= 50
    ]

    forbidden_genres = [
        genre
        for genre, score in book_dna.items()
        if isinstance(score, (int, float)) and score < 50
    ]

    return allowed_genres, forbidden_genres


GENRE_TERMS = {
    "romance": ["romance", "romantic", "romantically", "romancers"],
    "fantasy_romantasy": ["fantasy", "fantasies", "fantasy-fiction", "romantasy"],
    "thriller_mystery_crime": [
        "thriller", "thrillers", "mystery", "mysteries",
        "crime", "crimes", "criminal", "criminals",
    ],
    "science_fiction": [
        "science fiction", "sci-fi", "sci fi", "scifi", "science-fiction"
    ],
    "horror": ["horror", "horrors", "horrific"],
    "personal_development_nonfiction": [
        "self-help", "self help", "personal development", "nonfiction",
        "non-fiction", "non fiction",
    ],
    "young_adult": ["young adult", "ya fiction", "ya novel", "ya book"],
}

# Terms that identify a genre classification rather than an ordinary theme.
# We deliberately reject these when the corresponding genre is forbidden.
GENRE_CLASSIFICATION_PATTERNS = [
    r"\b{term}\b\s+(?:novel|book|story|tale|fiction|work|literature|narrative)",
    r"\b(?:dark|classic|modern|contemporary|literary|historical|psychological|gothic)\s+{term}\b",
    r"\b{term}\b\s+(?:experience|read|reading experience|narrative|story)\b",
    r"\b(?:a|an|the)\s+{term}\b",
    r"\b(?:is|as|offers|delivers|provides|makes|presents)\s+(?:a|an|the)?\s*{term}\b",
]


def _normalize_text(text: str) -> str:
    """Normalize generated text for deterministic policy checks."""
    text = text.lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def _genre_terms_for(genre: str) -> list[str]:
    return GENRE_TERMS.get(genre, [])


GENRE_TERMS = {
    "romance": ["romance", "romantic", "romantically"],
    "fantasy_romantasy": ["fantasy", "fantasies", "romantasy"],
    "thriller_mystery_crime": [
        "thriller", "thrillers", "mystery", "mysteries",
        "crime", "crimes", "criminal", "criminals",
    ],
    "science_fiction": [
        "science fiction", "sci-fi", "sci fi", "scifi", "science-fiction"
    ],
    "horror": ["horror", "horrors", "horrific"],
    "personal_development_nonfiction": [
        "self-help", "self help", "personal development", "nonfiction",
        "non-fiction", "non fiction",
    ],
    "young_adult": ["young adult", "ya fiction", "ya novel", "ya book"],
}


def _normalize_text(text: str) -> str:
    text = text.lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def get_forbidden_genre_terms(forbidden_genres: list[str]) -> list[str]:
    """Return every vocabulary variant forbidden by the Book DNA policy."""
    return [
        term
        for genre in forbidden_genres
        for term in GENRE_TERMS.get(genre, [])
    ]


def reason_uses_forbidden_genre(
    reason: str,
    forbidden_genres: list[str],
) -> bool:
    """Reject any explicit forbidden genre term in a generated reason.

    Recommendation reasons are short. The policy deliberately prefers a safe fallback
    over allowing an ambiguous genre mention to escape into the API response.
    """
    if not reason or not forbidden_genres:
        return False

    normalized_reason = _normalize_text(reason)
    forbidden_terms = get_forbidden_genre_terms(forbidden_genres)

    for term in forbidden_terms:
        if re.search(rf"\b{re.escape(term.lower())}\b", normalized_reason):
            return True

    return False


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[^.!?]+(?:[.!?]+|$)", text.strip()))


def _contains_disallowed_genre(reason: str, allowed_genres: list[str]) -> bool:
    """Reject any known genre vocabulary not explicitly allowed by Book DNA."""
    normalized = _normalize_text(reason)
    allowed_terms = {
        term.lower()
        for genre in allowed_genres
        for term in GENRE_TERMS.get(genre, [])
    }

    for terms in GENRE_TERMS.values():
        for term in terms:
            if term.lower() in allowed_terms:
                continue
            if re.search(rf"\b{re.escape(term.lower())}\b", normalized):
                return True

    return False


def validate_recommendation_reason(
    reason: str,
    book: BookResponse,
) -> bool:
    """Final deterministic policy gate before Gemini text reaches the API response."""
    if not isinstance(reason, str):
        return False

    reason = reason.strip()
    if not reason:
        return False

    if _word_count(reason) > 25:
        return False

    if _sentence_count(reason) != 1:
        return False

    normalized = _normalize_text(reason)
    forbidden_phrases = (
        "classic",
        "compatibility score",
        "page range",
        "number of pages",
        "pages",
        "great choice",
        "you will love",
        "selected options",
    )
    if any(phrase in normalized for phrase in forbidden_phrases):
        return False

    allowed_genres, forbidden_genres = get_allowed_genres(book.book_dna)

    if reason_uses_forbidden_genre(reason, forbidden_genres):
        return False

    if _contains_disallowed_genre(reason, allowed_genres):
        return False

    return True


def get_fallback_preference_weights(
    preferences: RecommendationRequest,
) -> dict[str, int]:
    """
    Converts the user's recommendation preferences into weights
    for Reading Profile characteristics.

    Higher weight = more important to the user.
    """

    weights = {
        "emotional": 0,
        "mysterious": 0,
        "easy_to_read": 0,
        "tearjerker": 0,
        "dark": 0,
        "intellectually_challenging": 0,
        "relaxing": 0,
        "thought_provoking": 0,
        "wholesome": 0,
    }

    looking_for_mapping = {
        "emotional": "emotional",
        "mysterious": "mysterious",
        "easy_to_read": "easy_to_read",
        "tearjerker": "tearjerker",
        "dark": "dark",
        "intellectually_challenging": "intellectually_challenging",
    }

    for preference in preferences.looking_for:
        characteristic = looking_for_mapping.get(preference)

        if characteristic:
            weights[characteristic] += 3

    mood_mapping = {
        "emotional": "emotional",
        "thought_provoking": "thought_provoking",
        "dark": "dark",
        "relaxing": "relaxing",
        "wholesome": "wholesome",
    }

    mood_characteristic = mood_mapping.get(preferences.mood)

    if mood_characteristic:
        weights[mood_characteristic] += 3

    return weights


def get_top_reading_characteristics(
    book: BookResponse,
    preferences: RecommendationRequest,
) -> list[str]:
    """
    Selects the strongest Reading Profile characteristics for this
    specific book according to the user's preferences.
    """

    profile = book.reading_profile or {}

    preference_weights = get_fallback_preference_weights(
        preferences
    )

    scored_characteristics = []

    for characteristic, profile_score in profile.items():
        if characteristic not in preference_weights:
            continue

        if not isinstance(profile_score, (int, float)):
            continue

        if profile_score < 50:
            continue

        preference_weight = preference_weights[characteristic]

        # Book characteristic is the primary factor.
        # User preference increases its relevance.
        final_score = (
            profile_score * 0.7
            + preference_weight * 10
        )

        scored_characteristics.append(
            (
                characteristic,
                final_score,
                profile_score,
            )
        )

    scored_characteristics.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return [
        characteristic
        for characteristic, _, _ in scored_characteristics[:3]
    ]


def generate_fallback_reason(
    book: BookResponse,
    preferences: RecommendationRequest,
) -> str:
    """
    Generates a deterministic personalized recommendation reason.

    This fallback:
    - never uses Book DNA genres;
    - never asks Gemini for anything;
    - uses only Reading Profile + user preferences;
    - produces deterministic output;
    - prevents forbidden genre hallucinations.
    """

    characteristics = get_top_reading_characteristics(
        book,
        preferences,
    )

    if not characteristics:
        return (
            "This book offers a distinctive reading experience "
            "with meaningful themes and engaging ideas."
        )

    characteristic_phrases = {
        "dark": "dark",
        "mysterious": "mysterious",
        "intellectually_challenging": (
            "intellectually challenging"
        ),
        "thought_provoking": "thought-provoking",
        "emotional": "emotional",
        "tearjerker": "emotionally intense",
        "easy_to_read": "accessible",
        "relaxing": "gentle and relaxing",
        "wholesome": "warm and comforting",
    }

    phrases = [
        characteristic_phrases[characteristic]
        for characteristic in characteristics
        if characteristic in characteristic_phrases
    ]

    if len(phrases) >= 3:
        return (
            f"This {phrases[0]}, {phrases[1]}, and {phrases[2]} "
            "experience offers meaningful thematic depth."
        )

    if len(phrases) == 2:
        return (
            f"This {phrases[0]} and {phrases[1]} experience "
            "offers meaningful thematic depth."
        )

    return (
        f"This {phrases[0]} reading experience offers "
        "meaningful themes and lasting impact."
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



def _build_reason_prompt(
    books: list[BookResponse],
    preferences: RecommendationRequest,
) -> str:
    books_information = []

    for index, book in enumerate(books, start=1):
        allowed_genres, forbidden_genres = get_allowed_genres(book.book_dna)
        books_information.append(
            f"""
BOOK {index}

Title:
{book.title}

Authors:
{", ".join(book.authors)}

Book DNA:
{json.dumps(book.book_dna or {}, ensure_ascii=False)}

ALLOWED GENRES — MAY BE USED:
{", ".join(allowed_genres) if allowed_genres else "None"}

FORBIDDEN GENRES — MUST NEVER BE USED:
{", ".join(forbidden_genres) if forbidden_genres else "None"}

Reading Profile:
{json.dumps(book.reading_profile or {}, ensure_ascii=False)}
"""
        )

    books_text = "\n".join(books_information)

    return f"""
You are a personalized book recommendation assistant.

Generate exactly one concise personalized reason for every provided book.

USER PREFERENCES

Genres:
{", ".join(preferences.genres)}

Looking For:
{", ".join(preferences.looking_for) if preferences.looking_for else "None"}

Mood:
{preferences.mood}

Page Range:
{preferences.page_range}

BOOKS

{books_text}

STRICT POLICY — THESE RULES ARE MANDATORY

1. Book DNA is the source of truth for genres.
2. A genre is allowed only when its Book DNA score is >= 50.
3. A genre with a score below 50 is forbidden, even if the user selected it.
4. Never describe, label, classify, or imply a book as a forbidden genre.
5. Do not turn a Reading Profile characteristic into a genre.
6. Darkness does not imply horror.
7. Mysterious does not imply thriller or mystery genre.
8. Emotional does not imply romance genre.
9. Supernatural, gothic, tragic, or disturbing elements do not automatically imply horror or fantasy.
10. If you are uncertain whether a genre is allowed, DO NOT mention the genre.
11. Prefer Reading Profile characteristics when explaining compatibility.
12. Do not mention any genre that is not in that book's ALLOWED GENRES list.

REASON RULES

- English only.
- Maximum 25 words.
- Exactly one sentence.
- Do not summarize plot.
- Do not mention score, pages, page range, or selected options.
- Do not call any book a classic.
- Do not invent characteristics.
- Do not use generic phrases such as "This book is a great choice." or "You will love this book."
- Make every reason specific to its book.
- Return exactly one reason for every provided book.
- Return no books that were not provided.

OUTPUT

Return ONLY valid JSON with exactly this structure:
{{
  "reasons": [
    {{
      "title": "Exact book title",
      "reason": "One concise sentence explaining why the user might enjoy this book."
    }}
  ]
}}
"""


def generate_recommendation_reasons(
    books: list[BookResponse],
    preferences: RecommendationRequest,
) -> dict[str, str]:
    """Generate reasons once, then enforce all semantic policy locally."""
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
            model="gemini-3.5-flash",
            contents=prompt,
        )

        if not response.text:
            print("⚠️ Gemini returned no recommendation reasons. Using fallback reasons.")
            return fallback

        print("🔎 GEMINI RAW RESPONSE:")
        print(repr(response.text))

        result = json.loads(response.text)
        reasons = result.get("reasons")

        if not isinstance(reasons, list):
            print("⚠️ Gemini returned invalid recommendation reasons. Using fallback reasons.")
            return fallback

        valid_books = {book.title: book for book in books}
        reason_map: dict[str, str] = {}

        for item in reasons:
            if not isinstance(item, dict):
                continue

            title = item.get("title")
            reason = item.get("reason")

            if not isinstance(title, str) or not isinstance(reason, str):
                continue
            if title not in valid_books:
                print(f"⚠️ Ignoring reason for unknown book: {title}")
                continue

            book = valid_books[title]

            if not validate_recommendation_reason(reason, book):
                print(
                    f"⚠️ Rejected unsafe/invalid reason for '{title}'. "
                    "Using deterministic fallback."
                )
                reason_map[title] = fallback[title]
                continue

            reason_map[title] = reason.strip()

        for book in books:
            if book.title not in reason_map:
                print(f"⚠️ No valid Gemini reason for '{book.title}'. Using fallback.")
                reason_map[book.title] = fallback[book.title]

        return reason_map

    except Exception as error:
        print(
            "⚠️ Gemini unavailable while generating recommendation reasons: "
            f"{error}"
        )
        print("⚠️ Using fallback reasons for all recommended books.")
        return fallback