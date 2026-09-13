import { useState } from "react";
import {
  getRecommendations,
  type RecommendationBook,
} from "../../services/api";
import "./Recommendations.css";

const genres = [
  { value: "romance", label: "Romance" },
  { value: "fantasy_romantasy", label: "Fantasy / Romantasy" },
  {
    value: "thriller_mystery_crime",
    label: "Thriller / Mystery / Crime",
  },
  { value: "science_fiction", label: "Science Fiction" },
  { value: "horror", label: "Horror" },
  {
    value: "personal_development_nonfiction",
    label: "Personal Development / Nonfiction",
  },
  { value: "young_adult", label: "Young Adult" },
];

const lookingForOptions = [
  { value: "emotional", label: "Emotional" },
  { value: "mysterious", label: "Mysterious" },
  { value: "easy_to_read", label: "Easy to Read" },
  { value: "tearjerker", label: "Tearjerker" },
  { value: "short_book", label: "Short Book" },
  { value: "dark", label: "Dark" },
  {
    value: "intellectually_challenging",
    label: "Intellectually Challenging",
  },
];

const moods = [
  { value: "relaxing", label: "Relaxing" },
  { value: "emotional", label: "Emotional" },
  { value: "thought_provoking", label: "Thought-provoking" },
  { value: "dark", label: "Dark" },
  { value: "wholesome", label: "Wholesome" },
];

const pageRanges = [
  { value: "under_200", label: "Under 200 pages" },
  { value: "between_200_400", label: "200–400 pages" },
  { value: "over_400", label: "Over 400 pages" },
];

interface RecommendationsProps {
  onSelectBook?: (book: RecommendationBook) => void;
}

function Recommendations({
  onSelectBook,
}: RecommendationsProps) {
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedLookingFor, setSelectedLookingFor] = useState<string[]>(
    []
  );
  const [selectedMood, setSelectedMood] = useState("");
  const [selectedPageRange, setSelectedPageRange] = useState("");

  const [recommendations, setRecommendations] = useState<
    RecommendationBook[]
  >([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function toggleSelection(
    value: string,
    setSelectedValues: React.Dispatch<React.SetStateAction<string[]>>
  ) {
    setSelectedValues((current) => {
      if (current.includes(value)) {
        return current.filter((item) => item !== value);
      }

      return [...current, value];
    });
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();

    setError("");

    if (selectedGenres.length < 2) {
      setError("Choose at least two genres.");
      return;
    }

    if (!selectedMood) {
      setError("Choose a mood.");
      return;
    }

    if (!selectedPageRange) {
      setError("Choose a page range.");
      return;
    }

    setLoading(true);
    setRecommendations([]);

    try {
      const data = await getRecommendations({
        genres: selectedGenres,
        looking_for: selectedLookingFor,
        mood: selectedMood,
        page_range: selectedPageRange as
          | "under_200"
          | "between_200_400"
          | "over_400",
      });

      setRecommendations(data.recommendations);

      if (data.recommendations.length === 0) {
        setError(
          "No recommendations were found for these preferences."
        );
      }
    } catch (err) {
      console.error(err);

      setError(
        "We could not generate recommendations. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="recommendations-page">
      {/* DECORATIVE SCRAPBOOK ELEMENTS */}

      <span
        className="scrapbook-doodle doodle-star"
        aria-hidden="true"
      >
        ✦
      </span>

      <span
        className="scrapbook-doodle doodle-heart"
        aria-hidden="true"
      >
        ♥
      </span>

      <span
        className="scrapbook-doodle doodle-flower"
        aria-hidden="true"
      >
        ✿
      </span>

      <span
        className="scrapbook-doodle doodle-star-small"
        aria-hidden="true"
      >
        ✧
      </span>

      <span
        className="scrapbook-tape tape-top"
        aria-hidden="true"
      />

      <span
        className="scrapbook-tape tape-bottom"
        aria-hidden="true"
      />

      {/* HEADER */}

      <div className="recommendations-header">
        <span className="scrapbook-label">
          A LITTLE BOOKISH JOURNEY
        </span>

        <p className="recommendations-eyebrow">
          FIND YOUR NEXT BOOK
        </p>

        <h1>What are you in the mood for?</h1>

        <div className="header-paper-line" aria-hidden="true">
          <span />
          <span>♡</span>
          <span />
        </div>

        <p className="recommendations-description">
          Tell us what you like, what you are craving, and the kind
          of story you want to find.
        </p>
      </div>

      {/* FORM */}

      <form
        className="recommendations-form scrapbook-paper"
        onSubmit={handleSubmit}
      >
        <div className="paper-corner paper-corner-top" />
        <div className="paper-corner paper-corner-bottom" />

        <div className="recommendation-section">
          <div className="section-heading">
            <span
              className="section-icon"
              aria-hidden="true"
            >
              ♡
            </span>

            <div>
              <h2>Genres</h2>

              <p>
                Pick at least two genres you would be happy to
                receive.
              </p>
            </div>
          </div>

          <div className="option-grid">
            {genres.map((genre) => (
              <button
                key={genre.value}
                type="button"
                className={`option-button ${
                  selectedGenres.includes(genre.value)
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  toggleSelection(
                    genre.value,
                    setSelectedGenres
                  )
                }
              >
                {genre.label}

                {selectedGenres.includes(genre.value) && (
                  <span
                    className="button-mark"
                    aria-hidden="true"
                  >
                    ✓
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="handwritten-divider" aria-hidden="true">
          <span>✦</span>
          <div />
          <span>♥</span>
          <div />
          <span>✦</span>
        </div>

        <div className="recommendation-section">
          <div className="section-heading">
            <span
              className="section-icon"
              aria-hidden="true"
            >
              ✧
            </span>

            <div>
              <h2>Looking for</h2>

              <p>
                Tell us what kind of reading experience you want.
              </p>
            </div>
          </div>

          <div className="option-grid">
            {lookingForOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`option-button ${
                  selectedLookingFor.includes(option.value)
                    ? "selected"
                    : ""
                }`}
                onClick={() =>
                  toggleSelection(
                    option.value,
                    setSelectedLookingFor
                  )
                }
              >
                {option.label}

                {selectedLookingFor.includes(option.value) && (
                  <span
                    className="button-mark"
                    aria-hidden="true"
                  >
                    ✓
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="handwritten-divider" aria-hidden="true">
          <span>♡</span>
          <div />
          <span>✿</span>
          <div />
          <span>♡</span>
        </div>

        <div className="preference-columns">
          <div className="recommendation-section">
            <div className="section-heading">
              <span
                className="section-icon"
                aria-hidden="true"
              >
                ☾
              </span>

              <div>
                <h2>Mood</h2>

                <p>Choose the feeling you want from your read.</p>
              </div>
            </div>

            <div className="option-grid">
              {moods.map((mood) => (
                <button
                  key={mood.value}
                  type="button"
                  className={`option-button ${
                    selectedMood === mood.value
                      ? "selected"
                      : ""
                  }`}
                  onClick={() => setSelectedMood(mood.value)}
                >
                  {mood.label}

                  {selectedMood === mood.value && (
                    <span
                      className="button-mark"
                      aria-hidden="true"
                    >
                      ✓
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div className="recommendation-section">
            <div className="section-heading">
              <span
                className="section-icon"
                aria-hidden="true"
              >
                ✧
              </span>

              <div>
                <h2>Page range</h2>

                <p>How long do you want your next read to be?</p>
              </div>
            </div>

            <div className="option-grid">
              {pageRanges.map((range) => (
                <button
                  key={range.value}
                  type="button"
                  className={`option-button ${
                    selectedPageRange === range.value
                      ? "selected"
                      : ""
                  }`}
                  onClick={() =>
                    setSelectedPageRange(range.value)
                  }
                >
                  {range.label}

                  {selectedPageRange === range.value && (
                    <span
                      className="button-mark"
                      aria-hidden="true"
                    >
                      ✓
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <p className="recommendation-error">
            <span aria-hidden="true">♡</span>
            {error}
          </p>
        )}

        <button
          type="submit"
          className="recommendation-submit"
          disabled={loading}
        >
          <span aria-hidden="true">✦</span>

          {loading
            ? "Finding your books..."
            : "Find My Books"}

          <span aria-hidden="true">✦</span>
        </button>
      </form>

      {/* RESULTS */}

      {recommendations.length > 0 && (
        <section className="recommendation-results">
          <div className="results-header">
            <span className="scrapbook-label">
              HANDPICKED FOR YOU
            </span>

            <p className="recommendations-eyebrow">
              YOUR LITTLE STACK
            </p>

            <h2>Books picked for you</h2>

            <div className="results-decoration" aria-hidden="true">
              <span>✦</span>
              <div />
              <span>♡</span>
              <div />
              <span>✦</span>
            </div>
          </div>

          <div className="recommendation-cards">
            {recommendations.map((book, index) => (
              <article
                key={book.title}
                className={`recommendation-card card-${index + 1}`}
                onClick={() => onSelectBook?.(book)}
              >
                <div
                  className="card-tape"
                  aria-hidden="true"
                />

                <div className="card-sticker">
                  {index === 0
                    ? "♡"
                    : index === 1
                      ? "✦"
                      : "✿"}
                </div>

                {book.thumbnail && (
                  <div className="cover-frame">
                    <img
                      src={book.thumbnail}
                      alt={`Cover of ${book.title}`}
                      className="recommendation-cover"
                    />
                  </div>
                )}

                <div className="recommendation-card-content">
                  <span className="compatibility-score">
                    <span aria-hidden="true">✦</span>
                    {book.compatibility_score}% match
                  </span>

                  <h3>{book.title}</h3>

                  <p className="recommendation-author">
                    {book.authors.join(", ")}
                  </p>

                  {book.reason && (
                    <div className="reason-note">
                      <span
                        className="reason-label"
                        aria-hidden="true"
                      >
                        WHY IT FITS
                      </span>

                      <p className="recommendation-reason">
                        {book.reason}
                      </p>
                    </div>
                  )}

                  <span
                    className="card-bottom-mark"
                    aria-hidden="true"
                  >
                    read me ♡
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </section>
  );
}

export default Recommendations;