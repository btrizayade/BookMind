from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes.auth import router as auth_router
from app.routes.books import router as books_router
from app.routes.recommendations import router as recommendations_router


app = FastAPI()


Base.metadata.create_all(bind=engine)


# Only trusted frontend origins are allowed to make browser requests.
# Credentials are enabled because authentication uses secure cookies.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://book-mind-ashy.vercel.app",
    "http://localhost:5174",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Content-Type",
        "X-CSRF-Token",
    ],
    max_age=600,
)


@app.get("/")
def home():
    return {
        "message": "Bem-vindo ao BookMind! Descubra livros, explore histórias e encontre sua próxima grande leitura."
    }


app.include_router(auth_router)

app.include_router(books_router)

app.include_router(recommendations_router)
