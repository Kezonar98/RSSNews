// src/pages/Home.tsx
import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Box,
  Container,
  Heading,
  Stack,
  HStack,
  Button,
  Text,
} from '@chakra-ui/react';
import Header from '../components/Header';
import NewsCard from '../components/NewsCard';
import { fetchNews, fetchCategories, NewsItem } from '../services/api';
import { usePagination } from '../hooks/usePagination';
import Layout from '../components/Layout';

const ITEMS_PER_PAGE = 10;

export default function Home() {
  const [searchParams] = useSearchParams();
  const initialSearch = searchParams.get('search') ?? '';
  const [allNewsItems, setAllNewsItems] = useState<NewsItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>();
  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    (async () => {
      try {
        const cats = await fetchCategories();
        setCategories(cats);
      } catch (err) {
        console.error('Failed to load categories', err);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      let page = 1;
      let allItems: NewsItem[] = [];
      let totalPages = 1;

      try {
        do {
          const { items, totalPages: tp } = await fetchNews(
            page,
            ITEMS_PER_PAGE,
            selectedCategory
          );
          allItems = allItems.concat(items);
          totalPages = tp;
          page++;
        } while (page <= totalPages);

        setAllNewsItems(allItems);
        setCurrentPage(1);
      } catch (err) {
        console.error('Failed to load news', err);
      }
    })();
  }, [selectedCategory]);

  const handleSearch = (q: string) => {
    setSearchQuery(q);
    setCurrentPage(1);
  };

  const handleCategoryClick = (cat: string) => {
    setSelectedCategory(prev => (prev === cat ? undefined : cat));
    setSearchQuery('');
    setCurrentPage(1);
  };

  const filteredNews = useMemo(() => {
    if (!searchQuery) return allNewsItems;
    const q = searchQuery.toLowerCase();
    return allNewsItems.filter(item => {
      const title = item.title ?? '';
      const desc = item.description ?? '';
      return (
        title.toLowerCase().includes(q) ||
        desc.toLowerCase().includes(q)
      );
    });
  }, [allNewsItems, searchQuery]);

  const { totalPages, paginatedItems, pageWindow } = usePagination(
    filteredNews,
    currentPage,
    ITEMS_PER_PAGE
  );

  const displayedItems = paginatedItems.filter(
    item => item.id && item.title && Array.isArray(item.categories)
  );

  return (
    <Layout onSearch={handleSearch}>
      <Container centerContent pt={24} minH="100vh" zIndex={1}>
        <Header />

        <HStack spacing={2} wrap="nowrap" overflowX="auto" mb={4}>
          {categories.map(cat => (
            <Button
              key={cat}
              size="sm"
              minW="max-content"
              bg={selectedCategory === cat ? 'purple.700' : 'purple.500'}
              color="white"
              border="1px solid rgba(255,255,255,0.4)"
              boxShadow="sm"
              _hover={{
                bg: selectedCategory === cat ? 'purple.800' : 'purple.600',
                boxShadow: 'md',
              }}
              onClick={() => handleCategoryClick(cat)}
              opacity={0.9}
              borderRadius="full"
            >
              {cat}
            </Button>
          ))}
        </HStack>

        <Heading size="lg" mb={4} color="white">
          Latest News {selectedCategory && `(Category: ${selectedCategory})`}
        </Heading>

        <Stack spacing={6} w="100%" align="center" mb={6}>
          {displayedItems.length > 0 ? (
            displayedItems.map(item => (
              <NewsCard
                key={item.id}
                id={item.id}
                title={item.title}
                description={item.categories.join(', ')}
                {...(item.is_rewritten && { link: `/article/${item.id}` })}
              />
            ))
          ) : (
            <Text color="gray.300">No results for "{searchQuery}"</Text>
          )}
        </Stack>

        <HStack spacing={2} justify="center">
          <Button size="sm" onClick={() => setCurrentPage(1)} disabled={currentPage === 1}>
            1
          </Button>
          {pageWindow[0] > 2 && <Text color="white">…</Text>}
          {pageWindow.map(p => (
            <Button
              key={p}
              size="sm"
              bg={currentPage === p ? 'purple.700' : 'transparent'}
              color={currentPage === p ? 'white' : 'purple.300'}
              onClick={() => setCurrentPage(p)}
            >
              {p}
            </Button>
          ))}
          {pageWindow.length > 0 &&
            pageWindow[pageWindow.length - 1] < totalPages - 1 && (
              <Text color="white">…</Text>
          )}
          <Button
            size="sm"
            onClick={() => setCurrentPage(totalPages)}
            disabled={currentPage === totalPages}
          >
            {totalPages}
          </Button>
        </HStack>
      </Container>
    </Layout>
  );
}
