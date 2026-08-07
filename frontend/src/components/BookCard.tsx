import "./BookCard.css";
import type { Book } from "../types/book";

interface BookCardProps {
  book: Book;
}

function BookCard({ book }: BookCardProps) {
  return (
    <div className="card">
      <img
        className="book-cover"
        src={book.thumbnail ?? ""}
        alt={book.title}
      />

      <h2>{book.title}</h2>

      <p className="author">
        {book.authors.join(", ")}
      </p>

      <div className="info">
        <span>⭐ {book.google_rating ?? "-"}</span>

        {book.page_count && (
          <span>📄 {book.page_count} páginas</span>
        )}
      </div>

      {book.publisher && (
        <p>🏢 {book.publisher}</p>
      )}

      {book.published_year && (
        <p>📅 {book.published_year}</p>
      )}

      <h3>🧠 AI Summary</h3>

      <p className="summary">
        {book.ai_summary}
      </p>

      <a
        href={book.preview_link ?? "#"}
        target="_blank"
        rel="noreferrer"
      >
        Ler prévia →
      </a>
    </div>
  );
}

export default BookCard;