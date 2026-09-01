import json
import os

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


def generate_recommendation_reasons(
    books: list[BookResponse],
    preferences: RecommendationRequest,
) -> dict[str, str]:
    if not books:
        return {}

    books_information = []

    for index, book in enumerate(books, start=1):
        books_information.append(
            f"""
BOOK {index}

Title:
{book.title}

Authors:
{", ".join(book.authors)}

Book DNA:
{json.dumps(book.book_dna or {}, ensure_ascii=False)}

Reading Profile:
{json.dumps(book.reading_profile or {}, ensure_ascii=False)}
"""
        )

    books_text = "\n".join(books_information)

    prompt = f"""
You are a personalized book recommendation assistant.

Your task is to generate one concise personalized reason for each recommended
book based on the user's preferences and each book's characteristics.

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


HOW TO GENERATE THE REASONS

For each book:

1. Identify the strongest characteristics that match the user's preferences.

2. Use Book DNA to identify relevant genre compatibility.

3. Use Reading Profile to identify relevant emotional, thematic or
reading-experience compatibility.

4. Mention only characteristics that are meaningfully supported by the scores.

5. Focus on WHY this specific book fits this particular reader.

6. If several characteristics match, naturally combine the strongest one or two.

7. Each reason must be specific to its book.

8. Reasons should be naturally varied and should not use the same sentence
structure for every book.


GENRE ACCURACY RULE

Never describe a book as belonging to a genre if that genre's Book DNA score
is below 50.

If a genre score is below 50, do not mention that genre at all.

Examples:

- romance 80 → mentioning romance is allowed.
- horror 25 → mentioning horror is forbidden.
- fantasy_romantasy 5 → mentioning fantasy is forbidden.
- thriller_mystery_crime 20 → mentioning thriller or mystery is forbidden.
- young_adult 10 → mentioning young adult is forbidden.


IMPORTANT RULES

- Write every reason in English.
- Maximum 25 words per reason.
- Each reason must contain exactly one sentence.
- Do not summarize the plot.
- Do not mention the compatibility score.
- Do not mention the number of pages.
- Do not mention the user's page range.
- Do not mention that the user selected specific options.
- Do not simply repeat the user's preferences.
- Do not call any book a "classic".
- Do not invent genres, themes, moods or characteristics.
- Do not describe a characteristic as strong if its corresponding score is low.
- Prefer Reading Profile characteristics over weak genre associations.
- Do not use generic phrases such as "This book is a great choice."
- Do not use generic phrases such as "You will love this book."
- Make every reason specific to its book.
- Return one reason for every book provided.
- Do not omit any book.
- Do not create reasons for books that were not provided.


RETURN FORMAT

Return ONLY valid JSON.

Do not use Markdown.
Do not add explanations outside the JSON.
Do not add extra fields.

Use exactly this structure:

{{
    "reasons": [
        {{
            "title": "Exact book title",
            "reason": "One concise sentence explaining why the user might enjoy this book."
        }}
    ]
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )

        if not response.text:
            return {}

        result = json.loads(response.text)

        reasons = result.get("reasons")

        if not isinstance(reasons, list):
            print("⚠️ Gemini returned invalid recommendation reasons.")
            return {}

        valid_titles = {book.title for book in books}
        reason_map: dict[str, str] = {}

        for item in reasons:
            if not isinstance(item, dict):
                continue

            title = item.get("title")
            reason = item.get("reason")

            if (
                not isinstance(title, str)
                or not isinstance(reason, str)
                or not reason.strip()
            ):
                continue

            if title not in valid_titles:
                print(
                    f"⚠️ Gemini returned a reason for an unknown book: {title}"
                )
                continue

            reason_map[title] = reason.strip()

        return reason_map

    except Exception as error:
        print(
            f"⚠️ Gemini unavailable while generating recommendation reasons: "
            f"{error}"
        )
        return {}