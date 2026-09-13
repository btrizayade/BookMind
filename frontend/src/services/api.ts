const API_URL = "https://bookmind-api.onrender.com";

export interface RecommendationRequest {
  looking_for: string[];
  genres: string[];
  page_range: "under_200" | "between_200_400" | "over_400";
  mood: string;
}

export interface RecommendationBook {
  title: string;
  authors: string[];
  thumbnail: string | null;
  page_count: number | null;
  published_year: string | null;
  compatibility_score: number;
  reason: string | null;
}

export interface RecommendationResponse {
  recommendations: RecommendationBook[];
}

export async function searchBook(title: string) {
  const response = await fetch(
    `${API_URL}/books/search?title=${encodeURIComponent(title)}`
  );

  if (!response.ok) {
    throw new Error("Erro ao buscar livro.");
  }

  return response.json();
}

export async function getRecommendations(
  preferences: RecommendationRequest
): Promise<RecommendationResponse> {
  const response = await fetch(
    `${API_URL}/books/recommendations`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(preferences),
    }
  );

  if (!response.ok) {
    throw new Error("Erro ao buscar recomendações.");
  }

  return response.json();
}