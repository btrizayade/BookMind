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

      <h2 className="summary-title">
        AI Summary
      </h2>

      <div className="summary-box">

        <p
          className={
            longText
              ? "summary-text dropcap"
              : "summary-text"
          }
        >
          {summary}
        </p>

      </div>

      {book.categories && book.categories.length > 0 && (

        <>
        
          <h3 className="section-title">
            Categories
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

        </>

      )}

      {book.preview_link && (

        <a
          href={book.preview_link}
          target="_blank"
          rel="noreferrer"
          className="preview-link"
        >
          Read Preview →
        </a>

      )}

    </div>

  );
}

export default RightPage;