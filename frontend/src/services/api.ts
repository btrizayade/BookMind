const API_URL =  "http://localhost:8000";

const CSRF_HEADER_NAME = "X-CSRF-Token";

let csrfToken: string | null = null;

function isStateChangingMethod(method: string): boolean {
  const upperMethod = method.toUpperCase();

  return (
    upperMethod === "POST" ||
    upperMethod === "PUT" ||
    upperMethod === "PATCH" ||
    upperMethod === "DELETE"
  );
}

function getRequestOptions(
  method: string,
  options: RequestInit = {},
): RequestInit {
  const upperMethod = method.toUpperCase();
  const headers = new Headers(options.headers);

  return {
    ...options,
    method: upperMethod,
    credentials: "include",
    headers,
  };
}

async function refreshCsrfToken(): Promise<string> {
  const response = await fetch(
    `${API_URL}/auth/csrf`,
    {
      method: "GET",
      credentials: "include",
    },
  );

  const data = await response.json().catch(() => null);

  if (!response.ok || typeof data?.csrf_token !== "string") {
    throw new Error(
      data?.detail ??
        "Could not establish a secure session.",
    );
  }

  csrfToken = data.csrf_token;

  return data.csrf_token;
}

async function getCsrfToken(): Promise<string> {
  if (csrfToken) {
    return csrfToken;
  }

  return refreshCsrfToken();
}

async function getAuthenticatedRequestOptions(
  method: string,
  options: RequestInit = {},
): Promise<RequestInit> {
  const requestOptions = getRequestOptions(
    method,
    options,
  );

  const headers = new Headers(
    requestOptions.headers,
  );

  if (isStateChangingMethod(method)) {
    const token = await getCsrfToken();

    headers.set(
      CSRF_HEADER_NAME,
      token,
    );
  }

  return {
    ...requestOptions,
    headers,
  };
}

export interface BookSuggestion {
  title: string;
  subtitle: string | null;
  authors: string[];
  author: string | null;
  year: string | null;
  thumbnail: string | null;
  source: string;
  source_id: string;
}

export interface RecommendationBook {
  title: string;
  authors: string[];
  thumbnail: string | null;
  compatibility_score: number;
  reason: string | null;
}

interface RecommendationResponse {
  recommendations: RecommendationBook[];
}

interface RecommendationRequest {
  genres: string[];
  looking_for: string[];
  mood: string;
  page_range:
    | "under_200"
    | "between_200_400"
    | "over_400";
}

/* =====================================
   SEARCH
===================================== */

export async function searchBook(
  title: string,
  author?: string | null,
) {
  const response = await fetch(
    `${API_URL}/books/search?title=${encodeURIComponent(title)}${
      author
        ? `&author=${encodeURIComponent(author)}`
        : ""
    }`,
  );

  if (!response.ok) {
    throw new Error("Erro ao buscar livro.");
  }

  return response.json();
}

/* =====================================
   AUTOCOMPLETE
===================================== */

export async function suggestBooks(
  query: string,
): Promise<BookSuggestion[]> {
  const trimmedQuery = query.trim();

  if (trimmedQuery.length < 2) {
    return [];
  }

  const response = await fetch(
    `${API_URL}/books/suggest?q=${encodeURIComponent(
      trimmedQuery,
    )}`,
  );

  if (!response.ok) {
    throw new Error("Erro ao buscar sugestões.");
  }

  return response.json();
}

/* =====================================
   RECOMMENDATIONS
===================================== */

export async function getRecommendations(
  preferences: RecommendationRequest,
): Promise<RecommendationResponse> {
  const response = await fetch(
    `${API_URL}/books/recommendations`,
    await getAuthenticatedRequestOptions("POST", {
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(preferences),
    }),
  );

  if (!response.ok) {
    throw new Error("Erro ao buscar recomendações.");
  }

  return response.json();
}

/* =====================================
   AUTHENTICATION
===================================== */

export interface LoginResponse {
  message: string;
  csrf_token: string;
}

export interface RegisterResponse {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
}

/* =====================================
   LOGIN
===================================== */

export async function loginUser(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await fetch(
    `${API_URL}/auth/login`,
    getRequestOptions("POST", {
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        password,
      }),
    }),
  );

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Invalid email or password.",
    );
  }

  if (
    !data ||
    typeof data.csrf_token !== "string"
  ) {
    throw new Error(
      "Could not establish a secure session.",
    );
  }

  csrfToken = data.csrf_token;

  return data;
}

/* =====================================
   REGISTER
===================================== */

export async function registerUser(
  name: string,
  email: string,
  password: string,
): Promise<RegisterResponse> {
  const response = await fetch(
    `${API_URL}/auth/register`,
    getRequestOptions("POST", {
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name,
        email,
        password,
      }),
    }),
  );

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "We could not create your account. Please try again.",
    );
  }

  return data;
}

/* =====================================
   SESSION
===================================== */

export async function getCurrentUser() {
  const response = await fetch(
    `${API_URL}/auth/me`,
    getRequestOptions("GET"),
  );

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Your session is no longer valid.",
    );
  }

  return data;
}

export async function logoutUser(): Promise<void> {
  const response = await fetch(
    `${API_URL}/auth/logout`,
    await getAuthenticatedRequestOptions("POST"),
  );

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "We could not log you out. Please try again.",
    );
  }

  csrfToken = null;
}