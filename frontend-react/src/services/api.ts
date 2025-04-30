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

/**
 * Fetch a single page of news.
 *
 * @param page     - page number (1-based)
 * @param perPage  - number of items per page
 * @param category - optional base category filter
 */
export async function fetchNews(
  page: number = 1,
  perPage: number = 5,
  category?: string
): Promise<NewsPage> {
  const params: Record<string, unknown> = {
    page,
    limit: perPage,
  };
  if (category) params.category = category;
  const res = await axios.get<NewsPage>(NEWS_URL, { params });
  return res.data;
}

/** Fetch all available base categories */
export async function fetchCategories(): Promise<string[]> {
  const res = await axios.get<string[]>(CATEGORIES_URL);
  return res.data;
}
