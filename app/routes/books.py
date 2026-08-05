from fastapi import APIRouter

router = APIRouter()


@router.get("/books/search")
def search_books(title: str):
    return {
        "title": title
    }