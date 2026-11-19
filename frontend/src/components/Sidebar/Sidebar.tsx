import { useState } from "react";
import miniLogo from "../../assets/minilogo.png";
import searchIcon from "../../assets/search.png";
import findIcon from "../../assets/find.png";
import "./Sidebar.css";

export type ActivePage = "home" | "search" | "recommendations";

interface SidebarProps {
  activePage: ActivePage;
  isCollapsed: boolean;
  isMobileOpen: boolean;
  onHome: () => void;
  onSearch: () => void;
  onRecommendations: () => void;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
}

type ChevronDirection = "left" | "right" | "down";

function ChevronIcon({ direction }: { direction: ChevronDirection }) {
  return (
    <svg
      className={`sidebar-chevron sidebar-chevron-${direction}`}
      viewBox="0 0 16 16"
      aria-hidden="true"
      focusable="false"
    >
      <path d="m5 3 5 5-5 5" />
    </svg>
  );
}

function Sidebar({
  activePage,
  isCollapsed,
  isMobileOpen,
  onHome,
  onSearch,
  onRecommendations,
  onToggleCollapsed,
  onCloseMobile,
}: SidebarProps) {
  const [isNavigationExpanded, setIsNavigationExpanded] = useState(true);

  const navigationItems = [
    { page: "home" as const, label: "Início", icon: miniLogo, onClick: onHome },
    { page: "search" as const, label: "Buscar livros", icon: searchIcon, onClick: onSearch },
    {
      page: "recommendations" as const,
      label: "Recomendações",
      icon: findIcon,
      onClick: onRecommendations,
    },
  ];

  return (
    <aside
      id="bookmind-sidebar"
      role={isMobileOpen ? "dialog" : undefined}
      aria-modal={isMobileOpen ? true : undefined}
      className={`sidebar ${isCollapsed ? "sidebar-collapsed" : ""} ${
        isMobileOpen ? "sidebar-mobile-open" : ""
      }`}
      aria-label="Navegação do BookMind"
    >
      <div className="sidebar-brand">
        {!isCollapsed && <span>BookMind</span>}
        {isCollapsed ? (
          <button
            className="sidebar-expand-button"
            onClick={onToggleCollapsed}
            aria-label="Expandir navegação"
            aria-expanded={false}
            aria-controls="bookmind-sidebar"
            title="Expandir navegação"
            type="button"
          >
            <ChevronIcon direction="right" />
          </button>
        ) : (
          <button
            className="sidebar-collapse-button"
            onClick={onToggleCollapsed}
            aria-label="Recolher navegação"
            aria-expanded={true}
            aria-controls="bookmind-sidebar"
            title="Recolher navegação"
            type="button"
          >
            <ChevronIcon direction="left" />
          </button>
        )}
        <button
          className="sidebar-mobile-close"
          onClick={onCloseMobile}
          aria-label="Fechar navegação"
          title="Fechar navegação"
          type="button"
        >
          ×
        </button>
      </div>

      {!isCollapsed && (
        <div className="sidebar-group">
          <button
            className="sidebar-group-toggle"
            onClick={() => setIsNavigationExpanded((expanded) => !expanded)}
            aria-expanded={isNavigationExpanded}
            aria-controls="bookmind-primary-navigation"
            type="button"
          >
            <span>Navegação</span>
            <ChevronIcon direction={isNavigationExpanded ? "down" : "right"} />
          </button>

          {isNavigationExpanded && (
            <nav
              className="sidebar-nav"
              id="bookmind-primary-navigation"
              aria-label="Navegação principal"
            >
              {navigationItems.map((item) => (
                <button
                  key={item.page}
                  className={`sidebar-nav-link ${activePage === item.page ? "is-active" : ""}`}
                  onClick={() => {
                    item.onClick();
                    onCloseMobile();
                  }}
                  aria-current={activePage === item.page ? "page" : undefined}
                  title={item.label}
                  type="button"
                >
                  <img src={item.icon} alt="" aria-hidden="true" />
                  <span>{item.label}</span>
                </button>
              ))}
            </nav>
          )}
        </div>
      )}

      {isCollapsed && (
        <nav className="sidebar-rail" aria-label="Navegação principal">
          {navigationItems.map((item) => (
            <button
              key={item.page}
              className={`sidebar-rail-link ${activePage === item.page ? "is-active" : ""}`}
              onClick={() => {
                item.onClick();
                onCloseMobile();
              }}
              aria-label={item.label}
              aria-current={activePage === item.page ? "page" : undefined}
              title={item.label}
              type="button"
            >
              <img src={item.icon} alt="" aria-hidden="true" />
            </button>
          ))}
        </nav>
      )}
    </aside>
  );
}

export default Sidebar;
