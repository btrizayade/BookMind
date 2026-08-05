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

    return response.json()