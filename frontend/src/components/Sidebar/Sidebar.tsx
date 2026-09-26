import logo from "../../assets/logo.png";
import miniLogo from "../../assets/minilogo.png";
import searchIcon from "../../assets/search.png";
import findIcon from "../../assets/find.png";
import searchButton from "../../assets/search-button.png";
import findButton from "../../assets/find-button.png";
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
          <div className="sidebar-rail">
            <button
              className="sidebar-rail-toggle"
              onClick={onToggle}
              aria-label="Expand sidebar"
              title="Expand sidebar"
              type="button"
            >
              ‹
            </button>

            <img
              src={miniLogo}
              alt="BookMind"
              className="sidebar-rail-logo"
            />

            <button
              className="sidebar-rail-action"
              onClick={onSearch}
              aria-label="Search a Book"
              title="Search a Book"
              type="button"
            >
              <img
                src={searchIcon}
                alt=""
                aria-hidden="true"
              />
            </button>

            <button
              className="sidebar-rail-action"
              onClick={onRecommendations}
              aria-label="Find My Next Book"
              title="Find My Next Book"
              type="button"
            >
              <img
                src={findIcon}
                alt=""
                aria-hidden="true"
              />
            </button>
          </div>
        )
      ) : (
        <>
          <div className="sidebar-top">
            {hasContent && (
              <button
                className="sidebar-toggle sidebar-toggle-open"
                onClick={onToggle}
                aria-label="Collapse sidebar"
                title="Collapse sidebar"
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
          </div>

          <p className="subtitle">
            Discover your next favorite book with AI.
          </p>

          <div className="divider"></div>

            <button
              className="sidebar-action image-button"
              onClick={onSearch}
              type="button"
            >
              <img
                src={searchButton}
                alt=""
                aria-hidden="true"
              />
              <span>Search a Book</span>
            </button>

            <button
              className="sidebar-action image-button"
              onClick={onRecommendations}
              type="button"
            >
              <img
                src={findButton}
                alt=""
                aria-hidden="true"
              />
              <span>Find My Next Book</span>
            </button>

          <div className="divider"></div>

          <span className="quote">
            “Books are a uniquely portable magic.”
          </span>
        </>
      )}
    </aside>
  );
}

export default Sidebar;