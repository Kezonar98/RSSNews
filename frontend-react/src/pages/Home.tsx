// src/pages/Home.tsx
import { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Container,
  Heading,
  Stack,
  HStack,
  Button,
  Image,
  Text,
  IconButton,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { AiFillHome } from 'react-icons/ai';
import Header from '../components/Header';
import NewsCard from '../components/NewsCard';
import SearchBar from '../components/SearchBar';
import { fetchNews, fetchCategories, NewsItem } from '../services/api';
import stars from '../assets/stars.png';
import planet from '../assets/planet1.png';
import satellite from '../assets/satellite.png';
import station from '../assets/cosmicstation.png';
import astronaut from '../assets/austronaut.png';

const MotionBox = motion(Box);
const ITEMS_PER_PAGE = 10;

export default function Home() {
  const [allNewsItems, setAllNewsItems] = useState<NewsItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedCategory, setSelectedCategory] = useState<string>();
  const [searchQuery, setSearchQuery] = useState('');

  // Завантажити всі категорії
  useEffect(() => {
    (async () => {
      const cats = await fetchCategories();
      setCategories(cats);
    })();
  }, []);

  // При зміні обраної категорії — завантажити увесь масив новин цієї категорії
  useEffect(() => {
    (async () => {
      let page = 1;
      let allItems: NewsItem[] = [];
      let totalPages = 1;
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
    })();
  }, [selectedCategory]);

  // Обробник пошуку
  const handleSearch = (q: string) => {
    setSearchQuery(q);
    setCurrentPage(1);
  };

  // Відфільтрований масив (по title чи description)
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

  // Скільки сторінок після фільтрації
  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(filteredNews.length / ITEMS_PER_PAGE));
  }, [filteredNews]);

  // Які елементи показати на поточній сторінці
  const paginatedNews = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredNews.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredNews, currentPage]);

  // Вікно пагінації
  const pageWindow = useMemo(() => {
    const maxBtns = 10;
    let start = Math.max(1, currentPage - Math.floor(maxBtns / 2));
    let end = Math.min(totalPages, start + maxBtns - 1);
    if (end - start + 1 < maxBtns) {
      start = Math.max(1, end - maxBtns + 1);
    }
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [currentPage, totalPages]);

  const handleCategoryClick = (cat: string) => {
    setSelectedCategory(prev => (prev === cat ? undefined : cat));
  };

  return (
    <Box pos="relative" w="100%" minH="100vh" overflow="hidden">
      {/* Background */}
      <Box
        pos="absolute" top={0} left={0}
        w="100%" h="100%"
        backgroundImage={`url(${stars})`}
        backgroundRepeat="repeat"
        backgroundSize="contain"
        animation="moveStars 30s linear infinite"
        zIndex={-2}
      />

      {/* Celestial decorations */}
      <Box pos="absolute" top="20px" left="20px" w="180px" h="180px" animation="spin 60s linear infinite">
        <Image src={planet} alt="Planet" w="100%" h="100%" objectFit="contain" />
        <MotionBox
          pos="absolute" top="90px" left="90px"
          w="220px" h="220px" ml="-110px" mt="-110px"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 20, ease: 'linear' }}
          transformOrigin="center"
        >
          <Image
            src={satellite}
            alt="Satellite"
            pos="absolute" top="0" left="50%"
            transform="translateX(-50%)"
            boxSize="40px"
          />
        </MotionBox>
      </Box>
      <Image src={station} alt="Station" pos="absolute" top="500px" right="20px" boxSize="220px" animation="float 6s ease-in-out infinite" />
      <Image src={astronaut} alt="Astronaut" pos="absolute" top="600px" right="100px" boxSize="80px" animation="floatFast 4s ease-in-out infinite" />

      {/* Search + Home */}
      <Box pos="absolute" top="20px" right="20px" zIndex={2}>
        <HStack spacing={2}>
          <SearchBar onSearch={handleSearch} />
          <IconButton
            aria-label="Home"
            icon={<AiFillHome />}
            onClick={() => {
              setSearchQuery('');
              setSelectedCategory(undefined);
            }}
            size="md"
            bg="purple.600"
            color="white"
            _hover={{ bg: 'purple.700', boxShadow: '0 0 10px rgba(138,43,226,0.8)' }}
            borderRadius="full"
          />
        </HStack>
      </Box>

      <Container centerContent pt={24} zIndex={1}>
        <Header />

        {/* Categories */}
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
          {paginatedNews.length ? (
            paginatedNews.map(item => (
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

        {/* Pagination */}
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
          {pageWindow.at(-1)! < totalPages - 1 && <Text color="white">…</Text>}
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
