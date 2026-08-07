import logo from "../../assets/logo.png";
import "./Sidebar.css";

interface SidebarProps {
  title: string;
  setTitle: (value: string) => void;
  onSearch: () => void;
}

function Sidebar({
  title,
  setTitle,
  onSearch,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <img
        src={logo}
        alt="BookMind"
        className="logo"
      />

      <p className="subtitle">
        Discover your next favorite book with AI.
      </p>

      <div className="divider"></div>

      <label>Search book here...</label>

      <input
        type="text"
        placeholder="Digite o nome do livro..."
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />

      <button onClick={onSearch}>
        Search
      </button>

      <div className="divider"></div>

      <span className="quote">
        “A reader lives a thousand lives before he dies.”
      </span>
    </aside>
  );
}

export default Sidebar;