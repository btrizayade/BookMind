import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.schemas.book import BookResponse


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

Analyze the book below and return:
1. A concise explanation of why someone should read it.
2. A Book DNA representing how strongly the book belongs to each category.

Book title:
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

BOOK DNA CATEGORIES:

1. romance
2. fantasy_romantasy
3. thriller_mystery_crime
4. science_fiction
5. horror
6. personal_development_nonfiction
7. young_adult

SCORING:

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

IMPORTANT:

- Judge each category independently.
- A book can score highly in multiple categories.
- Do not assign a high score simply because a category appears in the description.
- Consider the actual nature, themes and genre of the book.
- Do not assume that "romance" means the book is a romantic novel.
- Young Adult refers to the target audience, not simply the age of the characters.
- Personal Development & Nonfiction should score very low for fictional works.
- Fantasy & Romantasy should score based on actual fantasy elements, not simply romance.
- Horror should reflect genuine horror/horror-related elements, not simply darkness or tragedy.

SUMMARY RULES:

- Write the summary in English.
- Return EXACTLY five bullet points.
- Start every bullet with "•".
- Maximum 15 words per bullet.
- Focus on what the reader will learn, experience or gain.
- Return exactly five bullets.

RETURN FORMAT:

Return ONLY valid JSON.
Do not use Markdown.
Do not add explanations outside the JSON.

Use exactly this structure:

{{
    "summary": "- First point\\n- Second point\\n- Third point\\n- Fourth point\\n- Fifth point",
    "book_dna": {{
        "romance": 0,
        "fantasy_romantasy": 0,
        "thriller_mystery_crime": 0,
        "science_fiction": 0,
        "horror": 0,
        "personal_development_nonfiction": 0,
        "young_adult": 0
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

        if "summary" not in result or "book_dna" not in result:
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

        return {
            "summary": result["summary"],
            "book_dna": book_dna,
        }

    except Exception as error:
        print(f"⚠️ Gemini unavailable: {error}")
        return None