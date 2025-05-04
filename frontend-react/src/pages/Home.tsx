// src/pages/Home.tsx
import { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Container,
  Heading,
  Stack,
  HStack,
  Button,
  Text,
  IconButton,
} from '@chakra-ui/react';
import { AiFillHome } from 'react-icons/ai';
import Header from '../components/Header';
import SearchBar from '../components/SearchBar';
import NewsCard from '../components/NewsCard';
import BackgroundDecorations from '../components/BackgroundDecorations';
import { fetchNews, fetchCategories, NewsItem } from '../services/api';
import { usePagination } from '../hooks/usePagination';

const ITEMS_PER_PAGE = 10;

export default function Home() {
  // state for all fetched news, category filter and search query
  const [allNewsItems, setAllNewsItems] = useState<NewsItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>();
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // fetch all categories on mount
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

  // fetch all news for selected category (all pages)
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

  // handle category click
  const handleCategoryClick = (cat: string) => {
    setSelectedCategory(prev => (prev === cat ? undefined : cat));
    setSearchQuery('');            // reset search when category changes
  };

  // handle search input
  const handleSearch = (q: string) => {
    setSearchQuery(q);
    setCurrentPage(1);
  };

  // filter news by search query
  const filteredNews = useMemo(() => {
    if (!searchQuery) return allNewsItems;
    const q = searchQuery.toLowerCase();
    return allNewsItems.filter(item => {
      const title = item.title ?? '';
      const desc = item.description ?? '';
      return title.toLowerCase().includes(q) ||
             desc.toLowerCase().includes(q);
    });
  }, [allNewsItems, searchQuery]);

  // pagination logic
  const { totalPages, paginatedItems, pageWindow } = usePagination(
    filteredNews,
    currentPage,
    ITEMS_PER_PAGE
  );

  return (
    <Box pos="relative" w="100%" minH="100vh">
      {/* Background decorations */}
      <BackgroundDecorations />

      {/* Search and Home buttons */}
      <Box pos="absolute" top="20px" right="20px" zIndex={2}>
        <HStack spacing={2}>
          <SearchBar onSearch={handleSearch} />
          <IconButton
            aria-label="Home"
            icon={<AiFillHome />}
            onClick={() => {
              setSearchQuery('');
              setSelectedCategory(undefined);
              setCurrentPage(1);
            }}
            size="md"
            bg="purple.600"
            color="white"
            _hover={{
              bg: 'purple.700',
              boxShadow: '0 0 10px rgba(138,43,226,0.8)',
            }}
            borderRadius="full"
          />
        </HStack>
      </Box>

      <Container centerContent pt={24} zIndex={1}>
        <Header />

        {/* Category buttons */}
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

        {/* News list */}
        <Stack spacing={6} w="100%" align="center" mb={6}>
          {paginatedItems.length > 0 ? (
            paginatedItems.map(item => (
              <NewsCard
                key={item.id}
                title={item.title}
                id={item.id}
                description={item.categories.join(', ')}
                link={item.link}
              />
            ))
          ) : (
            <Text color="gray.300">
              No results for "{searchQuery}"
            </Text>
          )}
        </Stack>

        {/* Pagination controls */}
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
          {pageWindow.length > 0 && (pageWindow[pageWindow.length - 1] < totalPages - 1) && (
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
    </Box>
  );
}
