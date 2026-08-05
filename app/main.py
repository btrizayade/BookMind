from fastapi import FastAPI
from app.routes.books import router as books_router

app = FastAPI()


@app.get("/")
def home():
    return {
        "message": "Bem-vindo ao BookMind! Descubra livros, explore histórias e encontre sua próxima grande leitura."
    }


app.include_router(books_router)