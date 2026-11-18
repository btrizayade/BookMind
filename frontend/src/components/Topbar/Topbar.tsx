import logout from "../../assets/logout.png";
import logo from "../../assets/minilogo.png";

import "./Topbar.css";

interface TopbarProps {
  isLoginPage: boolean;
  onLogin: () => void;
  onBack: () => void;
  onHome: () => void;
  userName: string | null;
  onLogout: () => void;
}

function Topbar({
  isLoginPage,
  onLogin,
  onBack,
  onHome,
  userName,
  onLogout,
}: TopbarProps) {
  return (
    <header className="topbar">
      <button
        type="button"
        className="topbar-brand"
        onClick={onHome}
        aria-label="BookMind home"
        title="BookMind home"
      >
        <img src={logo} alt="" aria-hidden="true" />
      </button>

      {isLoginPage ? (
        <button
          type="button"
          className="topbar-login"
          onClick={onBack}
        >
          back to BookMind
        </button>
      ) : userName ? (
        <div className="topbar-user">
          <span className="topbar-greeting">
            Olá, {userName}
          </span>

          <button
            type="button"
            className="topbar-logout"
            onClick={onLogout}
            aria-label="Log out"
          >
            <img
              src={logout}
              alt=""
              aria-hidden="true"
            />
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="topbar-login"
          onClick={onLogin}
        >
          login
        </button>
      )}
    </header>
  );
}

export default Topbar;
