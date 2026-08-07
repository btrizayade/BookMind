import type { Book } from "../../types/book";

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

function truncateTitle(title: string, maxLength = 60) {
  if (title.length <= maxLength) return title;

  return title.substring(0, title.lastIndexOf(" ", maxLength)) + "...";
}

function LeftPage({ book }: Props) {
  const publishedYear =
    book.published_year?.slice(0, 4) ?? "-";

  const rating =
    book.google_rating?.toFixed(1) ?? "-";

  return (
    <div className="page-content">

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
            ⭐ {rating}
          </p>

        </div>

      </div>

      <div className="book-divider"></div>

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

    </div>
  );
}

export default LeftPage;