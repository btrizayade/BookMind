import {
  useState,
  type SyntheticEvent,
} from "react";

import loginPaper from "../../assets/bookmind-login-paper.png";
import { loginUser } from "../../services/api";

import "./Login.css";

interface LoginProps {
  onBack: () => void;
}

function Login({ onBack }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(
    event: SyntheticEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");

    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password) {
      setError(
        "Please enter your email and password.",
      );
      return;
    }

    setLoading(true);

    try {
      const data = await loginUser(
        trimmedEmail,
        password,
      );

      localStorage.setItem(
        "bookmind_access_token",
        data.access_token,
      );

      onBack();
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "We could not log you in. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-intro">
        <p className="login-eyebrow">
          A LITTLE BOOKISH WELCOME
        </p>

        <h1>Welcome back to BookMind</h1>

        <p className="login-subtitle">
          Discover wonderful stories, one page at a time.
        </p>
      </div>

      <section className="login-composition">
        <img
          src={loginPaper}
          alt=""
          className="login-paper"
          aria-hidden="true"
        />

        <div className="login-content">
          <form
            className="login-form"
            onSubmit={handleSubmit}
          >
            <label htmlFor="login-email">
              LOGIN
            </label>

            <input
              id="login-email"
              name="email"
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              autoComplete="email"
            />

            <label htmlFor="login-password">
              SENHA
            </label>

            <input
              id="login-password"
              name="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              autoComplete="current-password"
            />

            {error && (
              <p className="login-error">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
            >
              {loading ? "Opening..." : "Log in"}
            </button>
          </form>

          <p className="login-register">
            Don't have an account?{" "}
            <button
              type="button"
              onClick={() => {
                // Cadastro será implementado depois.
              }}
            >
              Sign up
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}

export default Login;