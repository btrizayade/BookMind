import {
  useState,
  type FormEvent,
} from "react";

import loginPaper from "../../assets/bookmind-login-paper.png";
import signupPaper from "../../assets/sign-up.png";

import {
  loginUser,
  registerUser,
} from "../../services/api";

import "./Login.css";

interface LoginProps {
  onBack: () => void;
}

type AuthMode = "login" | "signup";

function Login({ onBack }: LoginProps) {
  const [mode, setMode] =
    useState<AuthMode>("login");

  const [animationKey, setAnimationKey] =
    useState(0);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] =
    useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setAnimationKey((current) => current + 1);

    setError("");
    setSuccess("");

    setPassword("");
    setConfirmPassword("");
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setSuccess("");

    const trimmedEmail =
      email.trim();

    /* =====================================
       LOGIN
    ===================================== */

    if (mode === "login") {
      if (!trimmedEmail || !password) {
        setError(
          "Please enter your email and password.",
        );

        return;
      }

      setLoading(true);

      try {
        await loginUser(
          trimmedEmail,
          password,
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

      return;
    }

    /* =====================================
       SIGN UP
    ===================================== */

    const trimmedName =
      name.trim();

    if (!trimmedName) {
      setError(
        "Please enter your name.",
      );

      return;
    }

    if (!trimmedEmail) {
      setError(
        "Please enter your email.",
      );

      return;
    }

    if (!password) {
      setError(
        "Please create a password.",
      );

      return;
    }

    if (password.length < 8) {
      setError(
        "Your password must contain at least 8 characters.",
      );

      return;
    }

    if (password !== confirmPassword) {
      setError(
        "Passwords do not match.",
      );

      return;
    }

    setLoading(true);

    try {
      await registerUser(
        trimmedName,
        trimmedEmail,
        password,
      );

      /*
       * Volta para o login depois de criar
       * a conta e mantém o email preenchido.
       */
      setMode("login");

      setPassword("");
      setConfirmPassword("");

      setSuccess(
        "Account created successfully. You can now log in.",
      );
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "We could not create your account. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  const isSignUp =
    mode === "signup";

  return (
    <main className="login-page">
      <div
        key={`intro-${animationKey}`}
        className="login-intro"
      >
        <p className="login-eyebrow">
          {isSignUp
            ? "A LITTLE BOOKISH BEGINNING"
            : "A LITTLE BOOKISH WELCOME"}
        </p>

        <h1>
          {isSignUp
            ? "Join BookMind"
            : "Welcome back to BookMind"}
        </h1>

        <p className="login-subtitle">
          {isSignUp
            ? "Create your little reading corner."
            : "Discover wonderful stories, one page at a time."}
        </p>
      </div>

      <section
        key={`composition-${animationKey}`}
        className={`login-composition ${
          isSignUp
            ? "signup-composition"
            : ""
        }`}
      >
        <img
          src={
            isSignUp
              ? signupPaper
              : loginPaper
          }
          alt=""
          className="login-paper"
          aria-hidden="true"
        />

        <div
          className={`login-content ${
            isSignUp
              ? "signup-content"
              : ""
          }`}
        >
          <form
            className={`login-form ${
              isSignUp
                ? "signup-form"
                : ""
            }`}
            onSubmit={handleSubmit}
          >
            {isSignUp && (
              <>
                <label htmlFor="signup-name">
                  NAME
                </label>

                <input
                  id="signup-name"
                  name="name"
                  type="text"
                  placeholder="your name"
                  value={name}
                  onChange={(event) =>
                    setName(
                      event.target.value,
                    )
                  }
                  autoComplete="name"
                />
              </>
            )}

            <label htmlFor="auth-email">
              EMAIL
            </label>

            <input
              id="auth-email"
              name="email"
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(event) =>
                setEmail(
                  event.target.value,
                )
              }
              autoComplete="email"
            />

            <label htmlFor="auth-password">
              PASSWORD
            </label>

            <input
              id="auth-password"
              name="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value,
                )
              }
              autoComplete={
                isSignUp
                  ? "new-password"
                  : "current-password"
              }
            />

            {isSignUp && (
              <>
                <label htmlFor="signup-confirm-password">
                  CONFIRM PASSWORD
                </label>

                <input
                  id="signup-confirm-password"
                  name="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={
                    confirmPassword
                  }
                  onChange={(event) =>
                    setConfirmPassword(
                      event.target.value,
                    )
                  }
                  autoComplete="new-password"
                />
              </>
            )}

            {error && (
              <p className="login-error">
                {error}
              </p>
            )}

            {success && (
              <p className="login-success">
                {success}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
            >
              {loading
                ? isSignUp
                  ? "Creating..."
                  : "Opening..."
                : isSignUp
                  ? "Create account"
                  : "Log in"}
            </button>
          </form>

          <p className="login-register">
            {isSignUp
              ? "Already have an account?"
              : "Don't have an account?"}{" "}

            <button
              type="button"
              onClick={() =>
                switchMode(
                  isSignUp
                    ? "login"
                    : "signup",
                )
              }
            >
              {isSignUp
                ? "Log in"
                : "Sign up"}
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}

export default Login;