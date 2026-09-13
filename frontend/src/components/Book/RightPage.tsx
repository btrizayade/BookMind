import type { Book } from "../../types/book";

interface Props {
  book: Book;
}

function RightPage({ book }: Props) {
  const summary =
    book.ai_summary ??
    book.description ??
    "No description available for this book.";

  const longText = summary.length > 250;

  return (
    <div className="page-content right-content">
      {/* Decorative scrapbook elements */}

      <span
        className="book-doodle book-doodle-star"
        aria-hidden="true"
      >
        ✦
      </span>

      <span
        className="book-doodle book-doodle-heart"
        aria-hidden="true"
      >
        ♡
      </span>

      {/* Section label */}

      <span className="book-paper-label">
        AI BOOK NOTE
      </span>

      <div className="summary-heading">
        <span
          className="summary-heading-icon"
          aria-hidden="true"
        >
          ✧
        </span>

        <h2 className="summary-title">
          AI Summary
        </h2>

        <span
          className="summary-heading-icon"
          aria-hidden="true"
        >
          ✧
        </span>
      </div>

      <div className="summary-decoration" aria-hidden="true">
        <span />
        <span>♡</span>
        <span />
      </div>

      {/* AI Summary */}

      <div className="summary-box">
        <div className="summary-note">
          <span
            className="note-tape"
            aria-hidden="true"
          />

          <p
            className={
              longText
                ? "summary-text dropcap"
                : "summary-text"
            }
          >
            {summary}
          </p>

          <span
            className="note-mark"
            aria-hidden="true"
          >
            ✦
          </span>
        </div>
      </div>

      {/* Categories */}

      {book.categories && book.categories.length > 0 && (
        <div className="book-categories-section">
          <div className="book-mini-divider" aria-hidden="true">
            <span>✿</span>
            <div />
            <span>✿</span>
          </div>

          <h3 className="section-title">
            Bookshelf
          </h3>

          <div className="categories">
            {book.categories.map((category) => (
              <span
                key={category}
                className="category"
              >
                {category}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Preview */}

      {book.preview_link && (
        <a
          href={book.preview_link}
          target="_blank"
          rel="noreferrer"
          className="preview-link"
        >
          Read Preview
          <span aria-hidden="true"></span>
        </a>
      )}

      <span
        className="book-handwritten-note"
        aria-hidden="true"
      >
        found between the pages...
      </span>
    </div>
  );
}

export default RightPage;