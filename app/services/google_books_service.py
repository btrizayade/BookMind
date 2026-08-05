import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.googleapis.com/books/v1/volumes"

API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")


def search_books(title: str):
    response = httpx.get(
        BASE_URL,
        params={
            "q": title,
            "key": API_KEY
        }
    )

    data = response.json()
    book = data["items"][0]
    volume = book["volumeInfo"]
    print(volume)

    return {
    "title": volume.get("title"),
    "authors": volume.get("authors"),
    "publisher": volume.get("publisher"),
    "page_count": volume.get("pageCount"),
    "published_year": volume.get("publishedDate"),
    "language": volume.get("language"),
    "categories": volume.get("categories"),
    "description": volume.get("description"),
    "preview_link": volume.get("previewLink"),
    "google_rating": volume.get("averageRating"),
    "ratings_count": volume.get("ratingsCount"),
    "thumbnail": volume.get("imageLinks", {}).get("thumbnail"),
    "ai_summary": None,
    "source": "Google Books"
}