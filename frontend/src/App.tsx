import { useState } from "react";
import "./App.css";

import Sidebar from "./components/Sidebar/Sidebar";
import BookView from "./components/Book/Book";

import { searchBook } from "./services/api";
import type { Book } from "./types/book";

function App() {
  const [title, setTitle] = useState("");
  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Alteração 1: aceitar event opcional e prevenir o comportamento padrão do form
  async function handleSearch(event?: React.FormEvent) {
    event?.preventDefault();

    if (!title.trim()) {
      return; // Não pesquisa se o título estiver vazio
    }

    setLoading(true);
    setError("");
    
    try {
      const data = await searchBook(title);
      setBook(data);
    } catch (err) {
      console.error(err);
      setError("Não foi possível encontrar este livro. Verifique o título e tente novamente.");
      setBook(null); // Alteração 2: limpar livro antigo em caso de erro
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      {/*
         Alteração 3: o layout agora considera loading e erro além de book.
         Aplicamos 'layout-book' se existe livro **ou** estamos em loading/erro.
       */}
      <div className={`layout ${book || loading || error ? "layout-book" : "layout-empty"}`}>
        
        <Sidebar
          title={title}
          setTitle={setTitle}
          onSearch={handleSearch} // Pressupomos que o Sidebar chama isso em <form onSubmit> ou botão
        />

        <div className="book-area">
          {loading ? (
            // Card de loading (feedback ao usuário)
            <div className="loading-card">
              <span className="loading-icon">📖</span>
              <h3>Buscando...</h3>
              <p>Estamos procurando o seu próximo livro!</p>
            </div>
          ) : error ? (
            // Card de erro (mostra apenas o erro)
            <div className="error-card">
              <div className="error-icon">📚</div>
              <div>
                <h3>Livro não encontrado</h3>
                <p>{error}</p>
              </div>
            </div>
          ) : book ? (
            // Se temos o livro, exibe normalmente
            <BookView book={book} />
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default App;
