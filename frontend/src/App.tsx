import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import "./App.css";

import Sidebar from "./components/Sidebar/Sidebar";
import BookView from "./components/Book/Book";
import Recommendations from "./components/Recommendations/Recommendations";

import {
  searchBook,
  suggestBooks,
  type BookSuggestion,
} from "./services/api";

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

  const [suggestions, setSuggestions] =
    useState<BookSuggestion[]>([]);

  const [showSuggestions, setShowSuggestions] =
    useState(false);

  const [suggestionsLoading, setSuggestionsLoading] =
    useState(false);

  const [highlightedSuggestionIndex, setHighlightedSuggestionIndex] =
    useState(-1);

  const searchRequestId = useRef(0);
  const skipAutocompleteRef = useRef(false);

  const hasContent = mainContent !== null;

  /*
   * AUTOCOMPLETE
   *
   * Executa sempre que o usuário altera o texto.
   * A busca só acontece a partir de 2 caracteres
   * e espera 100ms antes de chamar a API.
   */
  useEffect(() => {
    if (skipAutocompleteRef.current) {
      skipAutocompleteRef.current = false;
      setSuggestionsLoading(false);
      setHighlightedSuggestionIndex(-1);
      return;
    }

    const query = title.trim();

    if (query.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      setSuggestionsLoading(false);
      setHighlightedSuggestionIndex(-1);
      return;
    }

    const requestId = ++searchRequestId.current;

    const timeoutId = window.setTimeout(async () => {
      try {
        setSuggestionsLoading(true);

        const data = await suggestBooks(query);

        /*
         * Ignora respostas antigas.
         *
         * Exemplo:
         * usuário digita "grok"
         * depois "grokking"
         *
         * Se a resposta de "grok" chegar depois,
         * ela não sobrescreve as sugestões atuais.
         */
        if (requestId !== searchRequestId.current) {
          return;
        }

        setSuggestions(data);
        setShowSuggestions(data.length > 0);
        setHighlightedSuggestionIndex(-1);
      } catch (err) {
        if (requestId !== searchRequestId.current) {
          return;
        }

        console.error("Autocomplete error:", err);
        setSuggestions([]);
        setShowSuggestions(false);
        setHighlightedSuggestionIndex(-1);
      } finally {
        if (requestId === searchRequestId.current) {
          setSuggestionsLoading(false);
        }
      }
    }, 100);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [title]);

  /*
   * BUSCA COMPLETA DO LIVRO
   */
  async function handleSearch(event?: FormEvent) {
    event?.preventDefault();

    const trimmedTitle = title.trim();

    if (!trimmedTitle) {
      return;
    }

    searchRequestId.current += 1;
    setShowSuggestions(false);
    setSuggestions([]);
    setHighlightedSuggestionIndex(-1);

    setLoading(true);
    setError("");
    setBook(null);

    try {
      const data = await searchBook(trimmedTitle);
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

  /*
   * SELEÇÃO DE UMA SUGESTÃO
   */
  async function handleSelectSuggestion(
    suggestion: BookSuggestion
  ) {
    skipAutocompleteRef.current = true;
    searchRequestId.current += 1;

    setTitle(suggestion.title);

    setSuggestions([]);
    setHighlightedSuggestionIndex(-1);
    setShowSuggestions(false);

    setLoading(true);
    setError("");
    setBook(null);

    setMainContent("search");

    try {
      /*
       * Usa título + autor quando o autocomplete conseguiu
       * identificar o autor. Isso reduz ambiguidades entre
       * livros/edições com o mesmo título.
       */
      const data = await searchBook(
        suggestion.title,
        suggestion.author,
      );

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

  /*
   * ABRE A ÁREA DE BUSCA
   */
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

  /*
   * ABRE A ÁREA DE RECOMENDAÇÕES
   */
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

  /*
   * SELEÇÃO DE LIVRO NAS RECOMENDAÇÕES
   */
  async function handleSelectRecommendedBook(
    recommendedBook: {
      title: string;
    }
  ) {
    setMainContent("search");
    setLoading(true);
    setError("");
    setBook(null);

    setTitle(recommendedBook.title);

    try {
      const data = await searchBook(recommendedBook.title);

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

  /*
   * SIDEBAR
   */
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

                <div className="search-input-wrapper">
                  <input
                    type="text"
                    placeholder="Type a book title..."
                    value={title}
                    onChange={(event) => {
                      setTitle(event.target.value);
                      setHighlightedSuggestionIndex(-1);
                    }}
                    onKeyDown={(event: KeyboardEvent<HTMLInputElement>) => {
                      if (!showSuggestions || suggestions.length === 0) {
                        return;
                      }

                      if (event.key === "ArrowDown") {
                        event.preventDefault();
                        setHighlightedSuggestionIndex((current) =>
                          current < suggestions.length - 1 ? current + 1 : 0
                        );
                        return;
                      }

                      if (event.key === "ArrowUp") {
                        event.preventDefault();
                        setHighlightedSuggestionIndex((current) =>
                          current > 0 ? current - 1 : suggestions.length - 1
                        );
                        return;
                      }

                      if (event.key === "Escape") {
                        event.preventDefault();
                        setShowSuggestions(false);
                        setHighlightedSuggestionIndex(-1);
                        return;
                      }

                      if (event.key === "Enter" && highlightedSuggestionIndex >= 0) {
                        event.preventDefault();
                        const suggestion = suggestions[highlightedSuggestionIndex];
                        if (suggestion) {
                          void handleSelectSuggestion(suggestion);
                        }
                      }
                    }}
                    onFocus={() => {
                      if (suggestions.length > 0) {
                        setShowSuggestions(true);
                      }
                      setHighlightedSuggestionIndex(-1);
                    }}
                    autoComplete="off"
                  />

                  {showSuggestions && (
                    <div className="suggestions-dropdown">
                      {suggestionsLoading && (
                        <div className="suggestions-loading">
                          Searching books...
                        </div>
                      )}

                      {!suggestionsLoading &&
                        suggestions.map((suggestion, index) => (
                          <button
                            id={`book-suggestion-${index}`}
                            key={`${suggestion.source}-${suggestion.source_id}`}
                            type="button"
                            role="option"
                            aria-selected={
                              index === highlightedSuggestionIndex
                            }
                            className={`suggestion-item ${
                              index === highlightedSuggestionIndex
                                ? "suggestion-item-highlighted"
                                : ""
                            }`}
                            onMouseDown={(event) => {
                              event.preventDefault();
                            }}
                            onClick={() =>
                              handleSelectSuggestion(
                                suggestion
                              )
                            }
                          >
                            <div className="suggestion-cover">
                              {suggestion.thumbnail ? (
                                <img
                                  src={suggestion.thumbnail}
                                  alt=""
                                />
                              ) : (
                                <div className="suggestion-cover-placeholder">
                                  📖
                                </div>
                              )}
                            </div>

                            <div className="suggestion-info">
                              <strong>
                                {suggestion.title}
                              </strong>

                              {suggestion.subtitle && (
                                <span className="suggestion-subtitle">
                                  {suggestion.subtitle}
                                </span>
                              )}

                              <span className="suggestion-meta">
                                {suggestion.authors.length > 0
                                  ? suggestion.authors.join(", ")
                                  : "Unknown author"}

                                {suggestion.year &&
                                  ` · ${suggestion.year}`}
                              </span>
                            </div>
                          </button>
                        ))}
                    </div>
                  )}
                </div>

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