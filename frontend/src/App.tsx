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
        "Não foi possível encontrar este livro. Verifique o título e tente novamente."
      );

      setBook(null);
    } finally {
      setLoading(false);
    }
  }

  function handleOpenSearch() {
    const wasInitialState = !hasContent;

    setMainContent("search");
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

    try {
      const data = await searchBook(recommendedBook.title);

      setTitle(recommendedBook.title);
      setBook(data);
    } catch (err) {
      console.error(err);

      setError(
        "Não foi possível abrir este livro. Tente pesquisá-lo novamente."
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
                <span className="loading-icon">📖</span>

                <h3>Buscando...</h3>

                <p>
                  Estamos procurando o seu próximo livro!
                </p>
              </div>
            ) : error ? (
              <div className="error-card">
                <div className="error-icon">📚</div>

                <div>
                  <h3>Livro não encontrado</h3>
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
                <h1>Search a Book</h1>

                <p>
                  Search for a book and explore its
                  information and AI analysis.
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
                  Search
                </button>
              </form>
            )}
          </main>
        )}
      </div>
    </div>
  );
}

export default App;