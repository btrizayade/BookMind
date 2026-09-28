import logout from "../../assets/logout.png";

import "./Topbar.css";

interface TopbarProps {
  isLoginPage: boolean;
  onLogin: () => void;
  onBack: () => void;
  userName: string | null;
  onLogout: () => void;
}

function Topbar({
  isLoginPage,
  onLogin,
  onBack,
  userName,
  onLogout,
}: TopbarProps) {
  return (
    <header className="topbar">
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