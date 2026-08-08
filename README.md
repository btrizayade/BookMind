<div align="center">

<img width="1254" height="1254" alt="LOGO" src="https://github.com/user-attachments/assets/18e2e6c6-06ab-40a4-8c3e-f868f6198599" />

# 📚 BookMind

### Discover books. Powered by AI.

Search any book, explore detailed information from Google Books, generate AI-powered summaries with Gemini, and cache results for faster future searches.

🌐 **Live Demo:** https://book-mind-ashy.vercel.app/

⭐ If you enjoyed this project, consider giving it a star!

</div>

---

## ✨ Preview

<p align="center">

<img width="1877" height="886" alt="Captura de tela 2026-08-07 134342" src="https://github.com/user-attachments/assets/2912995a-25d8-4abb-86df-cc03ac5675b6" />

</p>

---

# 🚀 Features

- 📚 Search books using Google Books API
- 🤖 Generate AI-powered summaries with Gemini
- 💾 Cache searches in PostgreSQL (Neon)
- ⚡ FastAPI REST API
- 🎨 Modern React interface
- 📖 Detailed book metadata
- 🔍 Categories, ratings and preview links
- ☁️ Fully deployed online

---

# 🛠 Tech Stack

## Frontend

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)

---

## Backend

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge)

---

## Database

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-00E599?style=for-the-badge)

---

## APIs & AI

![Google Books](https://img.shields.io/badge/Google_Books-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-8E75FF?style=for-the-badge&logo=google-gemini&logoColor=white)

---

## Deployment

![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel)

---

# 🏗 Architecture

```text
                React + Vite
                      │
                      ▼
               FastAPI Backend
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
 Google Books API            Gemini API
         │                         │
         └────────────┬────────────┘
                      ▼
              PostgreSQL (Neon)
```

---

# ⚙ Running locally

Clone the repository

```bash
git clone https://github.com/btrizayade/BookMind.git
```

Backend

```bash
python -m venv .venv

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Frontend

```bash
cd frontend

npm install

npm run dev
```

---

# 📂 Project Structure

```text
BookMind
│
├── app
│   ├── database
│   ├── models
│   ├── repositories
│   ├── routes
│   ├── schemas
│   └── services
│
├── frontend
│   ├── src
│   ├── assets
│   ├── components
│   └── services
│
└── requirements.txt
```

---

# 🔮 Ideas for Future Improvements

- ⭐ Favorites
- 📚 Personal library
- 🌙 Dark mode
- ⚠ Graceful fallback when Gemini API is unavailable

---

# 🤝 Contributing

Contributions are welcome!

If you have ideas to improve BookMind, feel free to open an issue or submit a pull request.

---

<div align="center">

Made with a lot of ❤️ for books

</div>
