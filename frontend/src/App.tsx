import {
  useEffect,
  useRef,
  useState,
  type SubmitEvent,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";

import "./App.css";

import loadingIcon from "./assets/loading.png";
import yellowFrame from "./assets/yellow-canva.png";
import greenFrame from "./assets/green-canva.png";
import purpleFrame from "./assets/purple-canva.png";

import Sidebar, { type ActivePage } from "./components/Sidebar/Sidebar";
import Topbar from "./components/Topbar/Topbar";
import BookView from "./components/Book/Book";
import HomeNavigationPanel from "./components/HomeNavigationPanel";
import Recommendations from "./components/Recommendations/Recommendations";
import Login from "./pages/Login/Login";
import IllustratedFrame from "./components/IllustratedFrame";

import {
  getCurrentUser,
  logoutUser,
  searchBook,
  suggestBooks,
  type BookSuggestion,
} from "./services/api";

import type { Book } from "./types/book";

interface CurrentUser {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
}

type SidebarState =
  | "expanded-navigation-priority"
  | "navigation-collapsed"
  | "expanded-width-priority"
  | "width-collapsed";

function App() {
  const [title, setTitle] = useState("");
  const [book, setBook] = useState<Book | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [activePage, setActivePage] = useState<ActivePage>("home");

  const [sidebarState, setSidebarState] =
    useState<SidebarState>("expanded-navigation-priority");
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [hasVisitedRecommendations, setHasVisitedRecommendations] =
    useState(false);

  const [suggestions, setSuggestions] =
    useState<BookSuggestion[]>([]);

  const [showSuggestions, setShowSuggestions] =
    useState(false);

  const [suggestionsLoading, setSuggestionsLoading] =
    useState(false);

  const [highlightedSuggestionIndex, setHighlightedSuggestionIndex] =
    useState(-1);

  const [showLogin, setShowLogin] = useState(false);

  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null);

  const [homeEntryId, setHomeEntryId] = useState(0);

  const searchRequestId = useRef(0);
  const bookRequestId = useRef(0);
  const skipAutocompleteRef = useRef(false);
  const mobileMenuButtonRef = useRef<HTMLButtonElement>(null);
  const wasMobileSidebarOpen = useRef(false);
  /*
   * SESSÃO
   *
   * Verifica a sessão existente ao abrir o BookMind
   * e novamente quando a tela de login é fechada.
   */
  useEffect(() => {
    if (showLogin) {
      return;
    }

    let isMounted = true;

    async function loadCurrentUser() {
      try {
        const user = await getCurrentUser();

        if (isMounted) {
          setCurrentUser(user);
        }
      } catch {
        if (isMounted) {
          setCurrentUser(null);
        }
      }
    }

    void loadCurrentUser();

    return () => {
      isMounted = false;
    };
  }, [showLogin]);

  useEffect(() => {
    if (!isMobileSidebarOpen) {
      return;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsMobileSidebarOpen(false);
        return;
      }

      if (event.key !== "Tab") {
        return;
      }

      const sidebar = document.getElementById("bookmind-sidebar");
      const focusable = Array.from(
        sidebar?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)") ?? [],
      ).filter((button) => button.getClientRects().length > 0);

      if (focusable.length === 0) {
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const focusIsInsideSidebar = sidebar?.contains(document.activeElement);

      if (event.shiftKey && (!focusIsInsideSidebar || document.activeElement === first)) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && (!focusIsInsideSidebar || document.activeElement === last)) {
        event.preventDefault();
        first?.focus();
      }
    }

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [isMobileSidebarOpen]);

  useEffect(() => {
    if (isMobileSidebarOpen) {
      document
        .querySelector<HTMLButtonElement>("#bookmind-sidebar .sidebar-mobile-close")
        ?.focus();
    } else if (wasMobileSidebarOpen.current) {
      const focusTarget =
        mobileMenuButtonRef.current ??
        document.querySelector<HTMLButtonElement>(
          ".home-navigation-panel .home-panel-action",
        );
      focusTarget?.focus();
    }

    wasMobileSidebarOpen.current = isMobileSidebarOpen;
  }, [isMobileSidebarOpen]);

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
  async function handleSearch(event?: SubmitEvent<HTMLFormElement>) {
    event?.preventDefault();

    const trimmedTitle = title.trim();

    if (!trimmedTitle) {
      return;
    }

    searchRequestId.current += 1;
    const requestId = ++bookRequestId.current;

    setShowSuggestions(false);
    setSuggestions([]);
    setHighlightedSuggestionIndex(-1);

    setLoading(true);
    setError("");
    setBook(null);

    try {
      const data = await searchBook(trimmedTitle);

      if (requestId === bookRequestId.current) {
        setBook(data);
      }
    } catch (err) {
      console.error(err);

      if (requestId === bookRequestId.current) {
        setError(
          "It was not possible to find this book. Please try again."
        );

        setBook(null);
      }
    } finally {
      if (requestId === bookRequestId.current) {
        setLoading(false);
      }
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
    const requestId = ++bookRequestId.current;

    setTitle(suggestion.title);

    setSuggestions([]);
    setHighlightedSuggestionIndex(-1);
    setShowSuggestions(false);

    setLoading(true);
    setError("");
    setBook(null);

    setActivePage("search");

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

      if (requestId === bookRequestId.current) {
        setBook(data);
      }
    } catch (err) {
      console.error(err);

      if (requestId === bookRequestId.current) {
        setError(
          "It was not possible to find this book. Please try again."
        );

        setBook(null);
      }
    } finally {
      if (requestId === bookRequestId.current) {
        setLoading(false);
      }
    }
  }

  /*
   * ABRE A ÁREA DE BUSCA
   */
  function handleOpenSearch() {
    setShowLogin(false);
    setIsMobileSidebarOpen(false);

    if (activePage === "search") {
      return;
    }

    searchRequestId.current += 1;
    bookRequestId.current += 1;
    setActivePage("search");
    setBook(null);
    setLoading(false);
    setError("");
    setShowSuggestions(false);
    setSuggestions([]);
    setSuggestionsLoading(false);
    setHighlightedSuggestionIndex(-1);
  }

  /*
   * ABRE A ÁREA DE RECOMENDAÇÕES
   */
  function handleRecommendations() {
    setShowLogin(false);
    setIsMobileSidebarOpen(false);

    if (activePage === "recommendations") {
      return;
    }

    searchRequestId.current += 1;
    bookRequestId.current += 1;
    setActivePage("recommendations");
    setHasVisitedRecommendations(true);
    setError("");
    setBook(null);
    setLoading(false);
    setShowSuggestions(false);
    setSuggestions([]);
    setSuggestionsLoading(false);
    setHighlightedSuggestionIndex(-1);
  }

  /*
   * SELEÇÃO DE LIVRO NAS RECOMENDAÇÕES
   */
  async function handleSelectRecommendedBook(
    recommendedBook: {
      title: string;
    }
  ) {
    const requestId = ++bookRequestId.current;
    setActivePage("search");
    setLoading(true);
    setError("");
    setBook(null);

    setTitle(recommendedBook.title);

    try {
      const data = await searchBook(recommendedBook.title);

      if (requestId === bookRequestId.current) {
        setBook(data);
      }
    } catch (err) {
      console.error(err);

      if (requestId === bookRequestId.current) {
        setError(
          "It was not possible to find this book. Please try again."
        );

        setBook(null);
      }
    } finally {
      if (requestId === bookRequestId.current) {
        setLoading(false);
      }
    }
  }

  /*
   * VOLTA AO ESTADO INICIAL
   */
  function handleHome() {
    setHomeEntryId((current) => current + 1);
    setShowLogin(false);
    setIsMobileSidebarOpen(false);

    searchRequestId.current += 1;
    bookRequestId.current += 1;
    skipAutocompleteRef.current = false;

    setTitle("");
    setBook(null);
    setLoading(false);
    setError("");

    setActivePage("home");
    setHasVisitedRecommendations(false);

    setSuggestions([]);
    setShowSuggestions(false);
    setSuggestionsLoading(false);
    setHighlightedSuggestionIndex(-1);
  }

  /*
   * LOGOUT
   */
  async function handleLogout() {
    try {
      await logoutUser();
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      setCurrentUser(null);
      setShowLogin(false);
      handleHome();
    }
  }

  /*
   * VOLTA DO LOGIN COM UMA ENTRADA SUAVE
   */
  function handleTopbarBack() {
    setIsMobileSidebarOpen(false);
    searchRequestId.current += 1;
    bookRequestId.current += 1;
    skipAutocompleteRef.current = false;

    setTitle("");
    setBook(null);
    setLoading(false);
    setError("");

    setActivePage("home");
    setHasVisitedRecommendations(false);

    setSuggestions([]);
    setShowSuggestions(false);
    setSuggestionsLoading(false);
    setHighlightedSuggestionIndex(-1);

    setHomeEntryId((current) => current + 1);

    setShowLogin(false);
  }

  /*
   * SIDEBAR
   */
  function handleToggleSidebar() {
    setSidebarState((current) => {
      switch (current) {
        case "expanded-navigation-priority":
          return "navigation-collapsed";
        case "navigation-collapsed":
          return "expanded-width-priority";
        case "expanded-width-priority":
          return "width-collapsed";
        case "width-collapsed":
          return "expanded-navigation-priority";
      }
    });
  }

  const isSidebarCollapsed = sidebarState === "width-collapsed";
  const isNavigationExpanded = sidebarState !== "navigation-collapsed";

  const showSidebar = activePage !== "home" || showLogin;
  const isHomeLanding = activePage === "home" && !showLogin;

  return (
    <>
      <Topbar
        isLoginPage={showLogin}
        onLogin={() => {
          setShowLogin(true);
          setIsMobileSidebarOpen(false);
        }}
        onBack={handleTopbarBack}
        onHome={showLogin ? handleTopbarBack : handleHome}
        userName={currentUser?.name ?? null}
        onLogout={handleLogout}
      />

      <div className="page-scroll">
        <div
          className={`app-shell ${
            isHomeLanding
              ? "app-shell-home"
              : isSidebarCollapsed
                ? "app-shell-sidebar-collapsed"
                : ""
          }`}
        >
          {showSidebar && isMobileSidebarOpen && (
            <button
              className="sidebar-backdrop"
              onClick={() => setIsMobileSidebarOpen(false)}
              aria-label="Fechar navegação"
              type="button"
            />
          )}

          {showSidebar && (
            <div className="sidebar-slot">
              <Sidebar
                activePage={activePage}
                isCollapsed={isSidebarCollapsed}
                isNavigationExpanded={isNavigationExpanded}
                sidebarState={sidebarState}
                isMobileOpen={isMobileSidebarOpen}
                onHome={handleHome}
                onSearch={handleOpenSearch}
                onRecommendations={handleRecommendations}
                onToggleCollapsed={handleToggleSidebar}
                onCloseMobile={() => setIsMobileSidebarOpen(false)}
              />
            </div>
          )}

          <main className="app-main">
            {showSidebar && (
              <button
                ref={mobileMenuButtonRef}
                className="mobile-menu-toggle"
                onClick={() => setIsMobileSidebarOpen((open) => !open)}
                aria-expanded={isMobileSidebarOpen}
                aria-controls="bookmind-sidebar"
                aria-label={isMobileSidebarOpen ? "Fechar navegação" : "Abrir navegação"}
                type="button"
              >
                <span aria-hidden="true">☰</span>
                <span>Menu</span>
              </button>
            )}

            <div className="app-main-content" hidden={showLogin}>
              <div
                className={`app-page-content ${
                  activePage === "home"
                    ? "app-page-content-home"
                    : activePage === "search"
                      ? "app-page-content-centered"
                      : ""
                }`}
              >
                {activePage === "home" && (
                  <HomeNavigationPanel
                    key={homeEntryId}
                    onSearch={handleOpenSearch}
                    onRecommendations={handleRecommendations}
                  />
                )}

                  {hasVisitedRecommendations && (
                    <div
                      className="recommendations-page-slot"
                      hidden={activePage !== "recommendations"}
                    >
                      <Recommendations
                        onSelectBook={handleSelectRecommendedBook}
                      />
                    </div>
                  )}

                {activePage === "search" && (loading ? (
                    <IllustratedFrame
                      asset={greenFrame}
                      className="illustrated-frame-loading"
                    >
                      <div className="loading-card">
                        <img
                          className="loading-icon"
                          src={loadingIcon}
                          alt=""
                          aria-hidden="true"
                        />

                        <h3>Searching...</h3>

                        <p>
                          We are searching for your next great read!
                        </p>
                      </div>
                    </IllustratedFrame>
                  ) : error ? (
                    <IllustratedFrame
                      asset={purpleFrame}
                      className="illustrated-frame-error"
                    >
                      <div className="error-card">
                        <div className="error-icon">☕︎</div>

                        <div>
                          <h3>Book not found</h3>
                          <p>{error}</p>
                        </div>
                      </div>
                    </IllustratedFrame>
                  ) : book ? (
                    <BookView book={book} />
                  ) : (
                    <IllustratedFrame
                      asset={yellowFrame}
                      className="illustrated-frame-search"
                    >
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
                          onKeyDown={(
                            event: ReactKeyboardEvent<HTMLInputElement>
                          ) => {
                            if (
                              !showSuggestions ||
                              suggestions.length === 0
                            ) {
                              return;
                            }

                            if (event.key === "ArrowDown") {
                              event.preventDefault();

                              setHighlightedSuggestionIndex(
                                (current) =>
                                  current <
                                  suggestions.length - 1
                                    ? current + 1
                                    : 0
                              );

                              return;
                            }

                            if (event.key === "ArrowUp") {
                              event.preventDefault();

                              setHighlightedSuggestionIndex(
                                (current) =>
                                  current > 0
                                    ? current - 1
                                    : suggestions.length - 1
                              );

                              return;
                            }

                            if (event.key === "Escape") {
                              event.preventDefault();

                              setShowSuggestions(false);
                              setHighlightedSuggestionIndex(-1);

                              return;
                            }

                            if (
                              event.key === "Enter" &&
                              highlightedSuggestionIndex >= 0
                            ) {
                              event.preventDefault();

                              const suggestion =
                                suggestions[
                                  highlightedSuggestionIndex
                                ];

                              if (suggestion) {
                                void handleSelectSuggestion(
                                  suggestion
                                );
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
                              suggestions.map(
                                (suggestion, index) => (
                                  <button
                                    id={`book-suggestion-${index}`}
                                    key={`${suggestion.source}-${suggestion.source_id}`}
                                    type="button"
                                    role="option"
                                    aria-selected={
                                      index ===
                                      highlightedSuggestionIndex
                                    }
                                    className={`suggestion-item ${
                                      index ===
                                      highlightedSuggestionIndex
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
                                          src={
                                            suggestion.thumbnail
                                          }
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
                                          {
                                            suggestion.subtitle
                                          }
                                        </span>
                                      )}

                                      <span className="suggestion-meta">
                                        {suggestion.authors.length > 0
                                          ? suggestion.authors.join(
                                              ", "
                                            )
                                          : "Unknown author"}

                                        {suggestion.year &&
                                          ` · ${suggestion.year}`}
                                      </span>
                                    </div>
                                  </button>
                                )
                              )}
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
                    </IllustratedFrame>
                  ))}
              </div>
            </div>
            {showLogin && <Login onBack={() => setShowLogin(false)} />}
          </main>
        </div>
      </div>
    </>
  );
}

export default App;
