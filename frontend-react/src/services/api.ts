// src/services/api.ts
import axios from 'axios';

const NEWS_URL = import.meta.env.VITE_NEWS_API_URL!;
const CATEGORIES_URL = import.meta.env.VITE_CATEGORIES_API_URL!;

export interface NewsItem {
  id: string;
  title: string;
  link: string;
  published: string;
  source: string;
  categories: string[];
  description: string; // у списку це може бути короткий опис чи join(categories)
}

export interface NewsPage {
  items: NewsItem[];
  totalPages: number;
}

/**
 * FullNewsItem represents a single article with rewritten content.
 */
export interface FullNewsItem {
  id: string;
  title: string;
  rewritten_title: string;
  content_rewritten: string;
  published: string;
  source: string;
  categories: string[];
}

/**
 * Fetch a single page of news for listing.
 *
 * @param page     - page number (1-based)
 * @param perPage  - number of items per page
 * @param category - optional category filter
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
 *
 * @param id - the article's unique identifier
 */
export async function fetchNewsById(id: string): Promise<FullNewsItem> {
  const res = await axios.get<FullNewsItem>(`${NEWS_URL}/${id}`);
  return res.data;
}
