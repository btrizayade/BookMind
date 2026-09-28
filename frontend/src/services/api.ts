const API_URL = "https://bookmind-api.onrender.com";

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
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(preferences),
    },
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
  access_token: string;
  token_type: string;
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
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        email,
        password,
      }),
    },
  );

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      data?.detail ??
        "Invalid email or password.",
    );
  }

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
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        name,
        email,
        password,
      }),
    },
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