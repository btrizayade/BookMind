import logo from "../assets/logo.png";
import searchButton from "../assets/search-button.png";
import findButton from "../assets/find-button.png";
import "./HomeNavigationPanel.css";

interface HomeNavigationPanelProps {
  onSearch: () => void;
  onRecommendations: () => void;
}

function HomeNavigationPanel({
  onSearch,
  onRecommendations,
}: HomeNavigationPanelProps) {
  return (
    <section className="home-navigation-panel" aria-label="BookMind welcome panel">
      <img src={logo} alt="BookMind" className="home-panel-logo" />
      <p className="home-panel-subtitle">Discover your next favorite book with AI.</p>

      <nav className="home-panel-actions" aria-label="Get started">
        <button
          className="home-panel-action"
          onClick={onSearch}
          type="button"
        >
          <img src={searchButton} alt="" aria-hidden="true" />
          <span>Search a Book</span>
        </button>
        <button
          className="home-panel-action"
          onClick={onRecommendations}
          type="button"
        >
          <img src={findButton} alt="" aria-hidden="true" />
          <span>Find My Next Book</span>
        </button>
      </nav>

      <p className="home-panel-quote">“Books are a uniquely portable magic.”</p>
    </section>
  );
}

export default HomeNavigationPanel;
