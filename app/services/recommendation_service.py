from app.schemas.recommendation import RecommendationRequest


def calculate_genre_score(
    book_dna: dict | None,
    selected_genres: list[str],
) -> float:
    if not book_dna or not selected_genres:
        return 0

    scores = [
        book_dna.get(genre, 0)
        for genre in selected_genres
    ]

    return sum(scores) / len(scores)


def calculate_profile_score(
    reading_profile: dict | None,
    looking_for: list[str],
    page_count: int | None,
) -> float:
    if not reading_profile or not looking_for:
        return 0

    scores = []

    for preference in looking_for:
        if preference == "short_book":
            if page_count is None:
                continue

            scores.append(
                100 if page_count < 200 else 0
            )
            continue

        scores.append(
            reading_profile.get(preference, 0)
        )

    if not scores:
        return 0

    return sum(scores) / len(scores)


def calculate_mood_score(
    reading_profile: dict | None,
    mood: str,
) -> float:
    if not reading_profile:
        return 0

    return reading_profile.get(mood, 0)


def matches_page_range(
    page_count: int | None,
    page_range: str,
) -> bool:
    if page_count is None:
        return False

    if page_range == "under_200":
        return page_count < 200

    if page_range == "between_200_400":
        return 200 <= page_count <= 400

    if page_range == "over_400":
        return page_count > 400

    return False


def calculate_compatibility_score(
    book_dna: dict | None,
    reading_profile: dict | None,
    page_count: int | None,
    preferences: RecommendationRequest,
) -> int:
    genre_score = calculate_genre_score(
        book_dna,
        preferences.genres,
    )

    profile_score = calculate_profile_score(
        reading_profile,
        preferences.looking_for,
        page_count,
    )

    mood_score = calculate_mood_score(
        reading_profile,
        preferences.mood,
    )

    final_score = (
        genre_score * 0.40
        + profile_score * 0.35
        + mood_score * 0.25
    )

    return round(final_score)