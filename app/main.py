from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {
        "message": "Bem-vindo ao BookMind! Descubra livros, explore histórias e encontre sua próxima grande leitura."
    }