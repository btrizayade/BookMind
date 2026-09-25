import "./Topbar.css";

interface TopbarProps {
  isLoginPage: boolean;
  onLogin: () => void;
  onBack: () => void;
}

function Topbar({
  isLoginPage,
  onLogin,
  onBack,
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