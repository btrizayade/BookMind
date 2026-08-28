const API_URL = "http://localhost:8000";

export async function searchBook(title: string) {
  const response = await fetch(
    `${API_URL}/books/search?title=${encodeURIComponent(title)}`
  );

  if (!response.ok) {
    throw new Error("Erro ao buscar livro.");
  }

  return response.json();
}