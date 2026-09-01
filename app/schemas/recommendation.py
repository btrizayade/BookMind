from pydantic import BaseModel, Field
from typing import Literal


# ---------- REQUEST ----------

Genre = Literal[
    "romance",
    "fantasy_romantasy",
    "thriller_mystery_crime",
    "science_fiction",
    "horror",
    "personal_development_nonfiction",
    "young_adult",
]

LookingFor = Literal[
    "emotional",
    "mysterious",
    "easy_to_read",
    "tearjerker",
    "short_book",
    "dark",
    "intellectually_challenging",
]

Mood = Literal[
    "relaxing",
    "emotional",
    "thought_provoking",
    "dark",
    "wholesome",
]

PageRange = Literal[
    "under_200",
    "between_200_400",
    "over_400",
]


class RecommendationRequest(BaseModel):
    looking_for: list[LookingFor] = Field(
        min_length=0,
        max_length=7,
    )

    genres: list[Genre] = Field(
        min_length=2,
        max_length=4,
    )

    page_range: PageRange

    mood: Mood


# ---------- RESPONSE ----------

class RecommendationBook(BaseModel):
    title: str
    authors: list[str]
    thumbnail: str | None = None
    page_count: int | None = None
    published_year: str | None = None
    compatibility_score: int
    reason: str | None = None


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationBook]