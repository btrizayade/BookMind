import type { Book } from "../../types/book";
import BookDNA from "./BookDNA";

interface Props {
  book: Book;
}

function formatLanguage(language: string | null) {
  const languages: Record<string, string> = {
    en: "English",
    pt: "Portuguese",
    fr: "French",
    es: "Spanish",
    de: "German",
    it: "Italian",
    ja: "Japanese",
  };

  if (!language) return "-";

  return languages[language] ?? language;
}

function truncateTitle(title: string, maxLength = 50) {
  if (title.length <= maxLength) return title;

  const cut = title.lastIndexOf(" ", maxLength);

  return (
    title.substring(0, cut > 0 ? cut : maxLength) + "..."
  );
}

function LeftPage({ book }: Props) {
  const publishedYear =
    book.published_year?.slice(0, 4) ?? "-";

  const rating =
    book.google_rating?.toFixed(1) ?? "-";

  return (
    <div className="page-content">

      {/* =========================================
          BOOK HEADER
      ========================================= */}

      <div className="book-header">

        {book.thumbnail && (
          <img
            src={book.thumbnail}
            alt={book.title}
            className="book-cover"
          />
        )}

        <div className="book-info">

          <h2 className="book-title">
            {truncateTitle(book.title)}
          </h2>

          <p className="book-author">
            {book.authors.join(", ")}
          </p>

          <p className="book-rating">
            ★ {rating}
          </p>

        </div>
      </div>

      {/* =========================================
          DIVIDER
      ========================================= */}

      <div className="book-divider"></div>

      {/* =========================================
          BOOK INFORMATION
      ========================================= */}

      <div className="book-metadata">

        <div className="metadata-row">
          <span className="metadata-label">
            Publisher
          </span>

          <span className="metadata-value">
            {book.publisher ?? "-"}
          </span>
        </div>

        <div className="metadata-row">
          <span className="metadata-label">
            Language
          </span>

          <span className="metadata-value">
            {formatLanguage(book.language)}
          </span>
        </div>

        <div className="metadata-row">
          <span className="metadata-label">
            Pages
          </span>

          <span className="metadata-value">
            {book.page_count ?? "-"}
          </span>
        </div>

        <div className="metadata-row">
          <span className="metadata-label">
            Published
          </span>

          <span className="metadata-value">
            {publishedYear}
          </span>
        </div>

      </div>

      {/* =========================================
          BOOK DNA
      ========================================= */}

      <BookDNA dna={book.book_dna} />

    </div>
  );
}

export default LeftPage;