from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.book_repository import BookRepository
from app.schemas.recommendation import (
    RecommendationBook,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.recommendation_service import (
    calculate_compatibility_score,
    matches_page_range,
)


router = APIRouter(
    prefix="/books",
    tags=["Recommendations"],
)

repository = BookRepository()


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
)
def get_recommendations(
    preferences: RecommendationRequest,
    db: Session = Depends(get_db),
):
    books = repository.get_books_for_recommendation(db)

    scored_books = []

    for book in books:
        if not matches_page_range(
            book.page_count,
            preferences.page_range,
        ):
            continue

        score = calculate_compatibility_score(
            book_dna=book.book_dna,
            reading_profile=book.reading_profile,
        page_count=book.page_count,
        preferences=preferences,
        )

        scored_books.append(
            (book, score)
        )

    scored_books.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    recommendations = []

    for book, score in scored_books[:3]:
        recommendations.append(
            RecommendationBook(
                title=book.title,
                authors=book.authors.split(", "),
                thumbnail=book.thumbnail,
                page_count=book.page_count,
                published_year=book.published_year,
                compatibility_score=score,
                reason=None,
            )
        )

    return RecommendationResponse(
        recommendations=recommendations
    )