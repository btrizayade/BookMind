import { useState } from "react";
import "./App.css";

import Sidebar from "./components/Sidebar/Sidebar";
import BookView from "./components/Book/Book";
import Recommendations from "./components/Recommendations/Recommendations";

import { searchBook } from "./services/api";
import type { Book } from "./types/book";

type MainContent = "search" | "recommendations" | null;

function App() {
  const [title, setTitle] = useState("");
  const [book, setBook] = useState<Book | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [mainContent, setMainContent] =
    useState<MainContent>(null);

  const [isSidebarCollapsed, setIsSidebarCollapsed] =
    useState(false);

  const hasContent = mainContent !== null;

  async function handleSearch(event?: React.FormEvent) {
    event?.preventDefault();

    if (!title.trim()) {
      return;
    }

    setLoading(true);
    setError("");
    setBook(null);

    try {
      const data = await searchBook(title);
      setBook(data);
    } catch (err) {
      console.error(err);

      setError(
        "It was not possible to find this book. Please try again."
      );

      setBook(null);
    } finally {
      setLoading(false);
    }
  }

  function handleOpenSearch() {
    const wasInitialState = !hasContent;

    setMainContent("search");
    setBook(null);
    setLoading(false);
    setError("");

    if (wasInitialState) {
      setIsSidebarCollapsed(true);
    }
  }

  function handleRecommendations() {
    const wasInitialState = !hasContent;

    setMainContent("recommendations");
    setError("");
    setBook(null);
    setLoading(false);

    if (wasInitialState) {
      setIsSidebarCollapsed(true);
    }
  }

  async function handleSelectRecommendedBook(
    recommendedBook: {
      title: string;
    }
  ) {
    setMainContent("search");
    setLoading(true);
    setError("");
    setBook(null);

    try {
      const data = await searchBook(recommendedBook.title);

      setTitle(recommendedBook.title);
      setBook(data);
    } catch (err) {
      console.error(err);

      setError(
        "It was not possible to find this book. Please try again."
      );

      setBook(null);
    } finally {
      setLoading(false);
    }
  }

  function handleToggleSidebar() {
    if (!hasContent) {
      return;
    }

    setIsSidebarCollapsed((current) => !current);
  }

  return (
    <div className="container">
      <div
        className={`layout ${
          hasContent
            ? "layout-content"
            : "layout-empty"
        } ${
          hasContent && isSidebarCollapsed
            ? "layout-sidebar-collapsed"
            : ""
        }`}
      >
        <Sidebar
          onSearch={handleOpenSearch}
          onRecommendations={handleRecommendations}
          hasContent={hasContent}
          isSidebarCollapsed={isSidebarCollapsed}
          onToggle={handleToggleSidebar}
        />

        {hasContent && (
          <main className="book-area">
            {mainContent === "recommendations" ? (
              <Recommendations
                onSelectBook={handleSelectRecommendedBook}
              />
            ) : loading ? (
              <div className="loading-card">
                <span className="loading-icon">
                  𓇼 ⋆.˚ .⋆ 𓇼
                </span>

                <h3>Searching...</h3>

                <p>
                  We are searching for your next great read!
                </p>
              </div>
            ) : error ? (
              <div className="error-card">
                <div className="error-icon">☕︎</div>

                <div>
                  <h3>Book not found</h3>
                  <p>{error}</p>
                </div>
              </div>
            ) : book ? (
              <BookView book={book} />
            ) : (
              <form
                className="search-content"
                onSubmit={handleSearch}
              >
                <span
                  className="search-tape"
                  aria-hidden="true"
                />

                <span
                  className="search-paper-label"
                  aria-hidden="true"
                />

                <h1>Search a Book</h1>

                <div
                  className="search-decoration"
                  aria-hidden="true"
                >
                  <div />
                  <span>♡</span>
                  <div />
                </div>

                <p>
                  Search for a book and explore its information,
                  reading profile and AI analysis.
                </p>

                <input
                  type="text"
                  placeholder="Type a book title..."
                  value={title}
                  onChange={(event) =>
                    setTitle(event.target.value)
                  }
                />

                <button type="submit">
                  Search for Book
                </button>

                <span
                  className="search-note"
                  aria-hidden="true"
                >
                  a little literary treasure awaits for you
                </span>
              </form>
            )}
          </main>
        )}
      </div>
    </div>
  );
}

export default App;