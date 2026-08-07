import "./Book.css";

import openBook from "../../assets/open-book.png";
import LeftPage from "./LeftPage";
import RightPage from "./RightPage";

import type { Book } from "../../types/book";

interface Props {
  book: Book;
}

function BookView({ book }: Props) {
  return (
    <div className="book-container">

      <img
        src={openBook}
        alt="Open book"
        className="book-image"
      />

      <div className="book-overlay">

        <div className="left-page">
          <LeftPage book={book} />
        </div>

        <div className="right-page">
            <RightPage book={book} />
        </div>

      </div>

    </div>
  );
}

export default BookView;