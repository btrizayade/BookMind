 <escape char="\\"> </escape>
<div align="center">

<img width="1254" height="1254" alt="BookMind Logo" src="https://github.com/user-attachments/assets/18e2e6c6-06ab-40a4-8c3e-f868f6198599" />

# 📚 BookMind

### Discover books. Find your next favorite.

BookMind is an AI-powered book discovery platform that helps readers find books that match their interests, reading preferences, and current mood.

By combining literary analysis, structured book data, and a personalized recommendation engine, BookMind goes beyond traditional book searches to help readers discover what to read next.

🌐 **Live Demo:** [book-mind-ashy.vercel.app](https://book-mind-ashy.vercel.app/)

⭐ If you enjoy this project, consider giving it a star!

</div>

---

## ✨ Preview

<p align="center">

<img width="1877" height="886" alt="BookMind Preview" src="https://github.com/user-attachments/assets/2912995a-25d8-4abb-86df-cc03ac5675b6" />

</p>

---

## 🚀 Features

### 📚 Book Discovery
- Search for books using Google Books and Open Library.
- Explore book details, including authors, covers, descriptions, categories, ratings, and preview links.
- Retrieve and organize book metadata from external sources.

### 🤖 AI-Powered Literary Analysis
- Generate AI-powered book summaries using Google Gemini.
- Analyze genre characteristics through **Book DNA**.
- Evaluate reading experiences through **Reading Profile**.
- Identify themes, atmosphere, and story elements to enrich book information.
- Generate personalized explanations for book recommendations.

### 🎯 Personalized Recommendations
- Discover books based on selected genres and reading preferences.
- Find books that match a desired mood or reading experience.
- Filter recommendations by page count.
- Rank books using a weighted compatibility score.
- Receive personalized explanations of why each recommendation matches your preferences.

### 🔐 Authentication and Security
- User registration and login.
- Password hashing with Argon2-based password hashing support.
- JWT-based authentication using secure cookies.
- CSRF protection for state-changing requests.
- Authenticated sessions and logout.

### ⚡ Backend and Data Management
- FastAPI REST API.
- PostgreSQL database hosted on Neon.
- SQLAlchemy for database access.
- Alembic for database migrations.
- Persistent storage of book metadata, AI summaries, and literary analysis.

### 🎨 User Experience
- Interactive React interface.
- Book-inspired visual design.
- Integrated authentication experience.
- Responsive layout for different screen sizes.

---

## 🛠 Tech Stack

### Frontend

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)

### Backend

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-000000?style=for-the-badge)

### Database

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Neon](https://img.shields.io/badge/Neon-00E599?style=for-the-badge&logo=neon&logoColor=black)

### APIs and AI

![Google Books](https://img.shields.io/badge/Google_Books-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Open Library](https://img.shields.io/badge/Open_Library-6F9975?style=for-the-badge)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-8E75FF?style=for-the-badge&logo=google-gemini&logoColor=white)

### Deployment

![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)

---

## 🏗 Architecture

```text
                       React + TypeScript
                              │
                              ▼
                        FastAPI REST API
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
         Book Services    Gemini AI    Authentication
               │              │              │
        ┌──────┴──────┐       │              │
        ▼             ▼       │              ▼
 Google Books    Open Library │         JWT + Cookies
        │             │       │              │
        └──────┬──────┘       │              │
               └──────────────┴──────────────┘
                              │
                              ▼
                       PostgreSQL (Neon)
```

The frontend communicates with the FastAPI backend, which coordinates book discovery, literary analysis, recommendation scoring, and authentication.

Book information and analysis are persisted in PostgreSQL so previously processed books can be reused without unnecessarily repeating external requests.

---

## 🧬 The Recommendation Engine

One of BookMind's main features is its recommendation engine, which evaluates more than a book's conventional genre classification.

### Book DNA

Book DNA represents how strongly a book fits different genre categories. Each category receives a score from 0 to 100, allowing the recommendation engine to evaluate genre compatibility instead of relying exclusively on broad external classifications.

Current categories include:

- Romance
- Fantasy and romantasy
- Thriller, mystery, and crime
- Science fiction
- Horror
- Personal development and nonfiction
- Young adult

### Reading Profile

Reading Profile describes the experience a reader might have with a book. It evaluates characteristics such as:

- Emotional intensity
- Mystery and suspense
- Reading accessibility
- Tearjerker potential
- Dark atmosphere
- Intellectual challenge
- Relaxing qualities
- Thought-provoking themes
- Wholesome qualities

BookMind also derives a short-book preference from the book's page count.

### Compatibility Scoring

Recommendations are ranked using a weighted compatibility score:

| Component | Weight |
|---|---:|
| Genre compatibility | 40% |
| Reading preference compatibility | 35% |
| Mood compatibility | 25% |

The selected page range is used as a filtering criterion. After the initial ranking, BookMind can use Gemini to generate concise, personalized explanations for the recommended books, based on the reader's preferences and the available literary analysis.

This approach combines deterministic scoring with AI-generated explanations, making recommendations more specific than a simple genre-based search.

---

## 📖 How BookMind Works

### 1. Search for a book

Users search for a title through the BookMind interface. The backend retrieves available metadata from Google Books and Open Library.

### 2. Explore the book

BookMind presents information such as the title, author, cover, description, categories, ratings, and preview links.

### 3. Analyze the book

Google Gemini can generate a summary and analyze the book's genre characteristics, reading profile, themes, atmosphere, and story elements.

### 4. Find your next book

Users select their preferred genres, desired reading experience, mood, and page range. BookMind evaluates eligible books and ranks them according to the compatibility scoring system.

### 5. Understand the recommendations

Personalized explanations highlight the characteristics that make each recommended book relevant to the user's preferences.

### 6. Reuse stored data

Book metadata and literary analysis are stored in PostgreSQL, allowing previously processed books to be retrieved without unnecessarily repeating the same work.

---

## 🔐 Authentication

BookMind includes a backend authentication system integrated with the main application.

The authentication flow includes:

- Account registration and login.
- Password hashing rather than storing passwords in plaintext.
- JWT access tokens stored in `HttpOnly` cookies.
- CSRF protection for state-changing requests.
- User session validation and logout.

The access token is not directly accessible to frontend JavaScript, reducing its exposure to certain client-side attacks. Security also depends on correct cookie configuration, token validation, and deployment settings.

---

## ☁️ Deployment

BookMind's frontend and backend are deployed separately:

- **Frontend:** Vercel
- **Backend:** Render
- **Database:** PostgreSQL hosted on Neon

Deployment requires the appropriate environment variables to be configured in each hosting service. Production authentication also depends on the frontend and backend origins, cookie settings, CSRF handling, and CORS configuration being consistent.

---

## 📂 Project Structure

```text
BookMind/
│
├── app/
│   ├── database/
│   ├── models/
│   ├── repositories/
│   ├── routes/
│   ├── schemas/
│   ├── security/
│   ├── seed/
│   └── services/
│
├── frontend/
│   └── src/
│       ├── assets/
│       ├── components/
│       ├── pages/
│       └── services/
│
├── alembic/
├── alembic.ini
├── requirements.txt
└── ...
```

---

## 🔮 Future Improvements

- ⭐ Book favorites and personal reading lists.
- 📚 A personal library with reading status tracking.
- 💭 A **Should I Read It?** feature for evaluating a specific book against a reader's preferences.
- ✉️ Automated personalized reading digests.
- 🎯 Further improvements to recommendation quality and preference evaluation.

---

## 🤝 Contributing

Contributions and suggestions are welcome!

Feel free to open an issue to report a problem, suggest a feature, or discuss potential improvements. Pull requests are also welcome.

---

<div align="center">

Made with a lot of ❤️ for books.

</div>
