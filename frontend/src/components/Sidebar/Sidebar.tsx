import logo from "../../assets/logo.png";
import "./Sidebar.css";

interface SidebarProps {
  onSearch: () => void;
  onRecommendations: () => void;
  hasContent: boolean;
  isSidebarCollapsed: boolean;
  onToggle: () => void;
}

function Sidebar({
  onSearch,
  onRecommendations,
  hasContent,
  isSidebarCollapsed,
  onToggle,
}: SidebarProps) {
  return (
    <aside
      className={`sidebar ${
        isSidebarCollapsed ? "sidebar-collapsed" : ""
      }`}
    >
      {isSidebarCollapsed ? (
        hasContent && (
          <button
            className="sidebar-toggle sidebar-toggle-collapsed"
            onClick={onToggle}
            aria-label="Expand sidebar"
            type="button"
          >
            ›
          </button>
        )
      ) : (
        <>
          {hasContent && (
            <button
              className="sidebar-toggle sidebar-toggle-open"
              onClick={onToggle}
              aria-label="Collapse sidebar"
              type="button"
            >
              ‹
            </button>
          )}

          <img
            src={logo}
            alt="BookMind"
            className="logo"
          />

          <p className="subtitle">
            Discover your next favorite book with AI.
          </p>

          <div className="divider"></div>

          <button
            className="sidebar-action"
            onClick={onSearch}
            type="button"
          >
            Search a Book
          </button>

          <button
            className="sidebar-action"
            onClick={onRecommendations}
            type="button"
          >
            Find My Next Book
          </button>

          <div className="divider"></div>

          <span className="quote">
            “A reader lives a thousand lives before he dies.”
          </span>
        </>
      )}
    </aside>
  );
}

export default Sidebar;