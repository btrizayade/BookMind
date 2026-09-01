from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes.books import router as books_router
from app.routes.recommendations import router as recommendations_router


app = FastAPI()


Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://book-mind-ashy.vercel.app",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Bem-vindo ao BookMind! Descubra livros, explore histórias e encontre sua próxima grande leitura."
    }


app.include_router(books_router)

app.include_router(recommendations_router)