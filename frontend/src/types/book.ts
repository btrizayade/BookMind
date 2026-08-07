export interface Book {
  title: string;
  authors: string[];
  publisher: string | null;
  page_count: number | null;
  published_year: string | null;
  language: string | null;
  categories: string[] | null;
  description: string | null;
  preview_link: string | null;
  google_rating: number | null;
  ratings_count: number | null;
  thumbnail: string | null;
  ai_summary: string | null;
  source: string;
}