import os

from dotenv import load_dotenv
from google import genai

from app.schemas.book import BookResponse

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def generate_summary(book: BookResponse) -> str:

    prompt = f"""
You are an expert book reviewer.

Based on the information below, explain WHY someone should read this book.

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

Rules:

- Write in English.
- Return EXACTLY five bullet points.
- Start every bullet with "-".
- Maximum 15 words per bullet.
- Focus on what the reader will learn or gain.
- If the description is missing, use your own knowledge about the book.
- Return ONLY the bullet points.

Example:

- Learn practical software engineering principles.
- Improve clean coding habits.
- Master professional development practices.
- Reduce technical debt.
- Essential reading for developers.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
    )

    return response.text