import miniLogo from "../../assets/minilogo.png";
import searchIcon from "../../assets/search.png";
import findIcon from "../../assets/find.png";
import "./Sidebar.css";

export type ActivePage = "home" | "search" | "recommendations";
type SidebarState = "expanded-navigation-priority" | "navigation-collapsed" | "expanded-width-priority" | "width-collapsed";

interface SidebarProps {
  activePage: ActivePage;
  isCollapsed: boolean;
  isNavigationExpanded: boolean;
  sidebarState: SidebarState;
  isMobileOpen: boolean;
  onHome: () => void;
  onSearch: () => void;
  onRecommendations: () => void;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
}

type ChevronDirection = "left" | "right" | "up" | "down";

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
  isNavigationExpanded,
  sidebarState,
  isMobileOpen,
  onHome,
  onSearch,
  onRecommendations,
  onToggleCollapsed,
  onCloseMobile,
}: SidebarProps) {
  const toggleLabel = {
    "expanded-navigation-priority": "Recolher navega\u00e7\u00e3o vertical",
    "navigation-collapsed": "Expandir navega\u00e7\u00e3o vertical",
    "expanded-width-priority": "Recolher largura da navega\u00e7\u00e3o",
    "width-collapsed": "Expandir largura da navega\u00e7\u00e3o",
  }[sidebarState];
  const toggleDirection: ChevronDirection = {
    "expanded-navigation-priority": "up",
    "navigation-collapsed": "down",
    "expanded-width-priority": "left",
    "width-collapsed": "right",
  }[sidebarState] as ChevronDirection;

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
        <button
          className="sidebar-toggle-button"
          onClick={onToggleCollapsed}
          aria-label={toggleLabel}
          aria-expanded={isNavigationExpanded}
          aria-controls="bookmind-primary-navigation"
          title={toggleLabel}
          type="button"
        >
          <ChevronIcon direction={toggleDirection} />
        </button>
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

      {!isCollapsed && isNavigationExpanded && (
        <div className="sidebar-group">
          <span className="sidebar-group-label">{'Navega\u00e7\u00e3o'}</span>
          <nav
            className="sidebar-nav"
            id="bookmind-primary-navigation"
            aria-label={'Navega\u00e7\u00e3o principal'}
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
        </div>
      )}

      {!isCollapsed && !isNavigationExpanded && (
        <nav
          id="bookmind-primary-navigation"
          className="sidebar-nav"
          aria-label={'Navega\u00e7\u00e3o principal'}
          hidden
        />
      )}

      {isCollapsed && (
        <nav id="bookmind-primary-navigation" className="sidebar-rail" aria-label="Navegação principal">
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
