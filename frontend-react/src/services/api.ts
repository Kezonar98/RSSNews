import axios from 'axios';

const NEWS_URL       = import.meta.env.VITE_NEWS_API_URL!;
const CATEGORIES_URL = import.meta.env.VITE_CATEGORIES_API_URL!;

export interface NewsItem {
  id: string;
  title: string;
  link: string;
  published: string;
  source: string;
  categories: string[];
  description: string;
}

export interface NewsPage {
  items: NewsItem[];
  totalPages: number;
}

export interface FullNewsItem {
  id: string;
  title: string;
  rewritten_title: string;
  rewritten_body: string;
  published: string;
  source: string;
  categories: string[];
}

/**
 * Fetch a single page of news for listing.
 */
export async function fetchNews(
  page = 1,
  perPage = 5,
  category?: string
): Promise<NewsPage> {
  const params: Record<string, unknown> = { page, limit: perPage };
  if (category) params.category = category;
  const res = await axios.get<NewsPage>(NEWS_URL, { params });
  return res.data;
}

/**
 * Fetch all available categories.
 */
export async function fetchCategories(): Promise<string[]> {
  const res = await axios.get<string[]>(CATEGORIES_URL);
  return res.data;
}

/**
 * Fetch a single rewritten news article by ID.
 * This will check for the rewritten title and body from the backend.
 */
export async function fetchNewsById(id: string): Promise<FullNewsItem> {
  try {
    const res = await axios.get<FullNewsItem>(`${NEWS_URL}/${id}`);
    return res.data;
  } catch (error) {
    console.error("Error fetching news by ID:", error);
    throw new Error("Error fetching news by ID");
  }
}
