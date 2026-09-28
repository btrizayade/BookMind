<div align="center">

<img width="1254" height="1254" alt="LOGO" src="https://github.com/user-attachments/assets/18e2e6c6-06ab-40a4-8c3e-f868f6198599" />

# 📚 BookMind

### Discover books. Powered by AI.

BookMind is an AI-powered book discovery application that helps users search for books, explore detailed information, generate AI summaries, and discover their next read through a visual and interactive experience.

🌐 **Live Demo:** https://book-mind-ashy.vercel.app/

⭐ If you enjoyed this project, consider giving it a star!

</div>

---

## ✨ Preview

<p align="center">

<img width="1877" height="886" alt="BookMind Preview" src="https://github.com/user-attachments/assets/2912995a-25d8-4abb-86df-cc03ac5675b6" />

</p>

---

# 🚀 Features

- 📚 Search for books using the Google Books API
- 📖 View detailed book information, including authors, categories, ratings, and preview links
- 🤖 Generate AI-powered book summaries using Google Gemini
- 💾 Cache book data and generated summaries in PostgreSQL
- 🔐 User registration and login
- 👤 Authenticated user sessions
- 🚪 Secure logout
- 🔎 Find your next book through the **Find My Next Book** feature
- ⚡ FastAPI REST API
- 🎨 Interactive React interface with a book-inspired visual design
- ☁️ Deployed online with Vercel and Render

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
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-000000?style=for-the-badge)

---

## Database

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-00E599?style=for-the-badge&logo=neon&logoColor=black)

---

## APIs & AI

![Google Books](https://img.shields.io/badge/Google_Books-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75FF?style=for-the-badge&logo=google-gemini&logoColor=white)

---

## Deployment

![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)

---

# 🏗 Architecture

```text
                         React + Vite
                              │
                              ▼
                      FastAPI Backend
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      Google Books API    Gemini API      Authentication
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                       PostgreSQL (Neon)
```

The frontend communicates with the FastAPI backend, which integrates external book and AI services and stores cached data in PostgreSQL.

Authentication is handled by the backend using secure cookies and CSRF protection.

---

# 🔐 Authentication

BookMind includes an authentication system that allows users to:

- Create an account
- Log in securely
- Maintain an authenticated session
- See their name in the application after login
- Log out securely

The authentication flow is integrated into the main BookMind interface rather than existing as a completely separate application.

---

# 📚 How BookMind Works

### 1. Search for a book

Users can search for a book directly from the BookMind interface.

### 2. Explore the book

BookMind retrieves information such as:

- Title
- Author
- Cover
- Description
- Categories
- Ratings
- Preview links

### 3. Generate an AI summary

Google Gemini generates an AI-powered summary of the selected book.

The summary is displayed directly inside the BookMind book interface.

### 4. Cache the result

Book information and generated summaries are stored in PostgreSQL, allowing previously processed books to be retrieved without unnecessarily repeating external requests.

### 5. Find your next book

The **Find My Next Book** feature provides another way to discover books beyond directly searching for a title.

---

# ⚙️ Running Locally

## Clone the repository

```bash
git clone https://github.com/btrizayade/BookMind.git
cd BookMind
```

## Backend

Create a virtual environment:

```bash
python -m venv .venv
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

## Frontend

Open another terminal:

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
│   │   ├── assets
│   │   ├── components
│   │   ├── pages
│   │   └── services
│   └── ...
│
├── requirements.txt
└── ...
```

---

# 🔮 Future Improvements

- ⭐ Favorites
- 💭 Should I Read It?
- 🧬 Book DNA
- 📚 Personal library
- 🎯 More personalized recommendations

---

# 🤝 Contributing

Contributions are welcome!

If you have ideas to improve BookMind, feel free to open an issue or submit a pull request.

---

<div align="center">

Made with a lot of ❤️ for books

</div>
