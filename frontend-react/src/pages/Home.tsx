import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  Stack,
  HStack,
  Button,
  Image,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import Header from '../components/Header';
import NewsCard from '../components/NewsCard';
import { fetchNews, fetchCategories, NewsItem } from '../services/api';

import stars from '../assets/stars.png';
import planet from '../assets/planet1.png';
import satellite from '../assets/satellite.png';
import station from '../assets/cosmicstation.png';
import astronaut from '../assets/austronaut.png';

const MotionBox = motion(Box);

export default function Home() {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);

  useEffect(() => {
    (async () => {
      try {
        const cats = await fetchCategories();
        setCategories(cats);
      } catch (err) {
        console.error('[Home] fetchCategories error:', err);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const { items, totalPages } = await fetchNews(currentPage, 10, selectedCategory);
        setNewsItems(items);
        setTotalPages(totalPages);
      } catch (err) {
        console.error('[Home] fetchNews error:', err);
      }
    })();
  }, [currentPage, selectedCategory]);

  const handleCategoryClick = (cat: string) => {
    setSelectedCategory(prev => (prev === cat ? undefined : cat));
    setCurrentPage(1);
  };

  // compute sliding window of pages
  const pageWindow = React.useMemo(() => {
    const maxBtns = 10;
    let start = Math.max(1, currentPage - Math.floor(maxBtns / 2));
    let end = Math.min(totalPages, start + maxBtns - 1);
    if (end - start + 1 < maxBtns) {
      start = Math.max(1, end - maxBtns + 1);
    }
    const pages = [];
    for (let p = start; p <= end; p++) pages.push(p);
    return pages;
  }, [currentPage, totalPages]);

  return (
    <Box pos="relative" w="100%" minH="100vh" overflow="hidden">
      {/* falling stars */}
      <Box
        pos="absolute" top={0} left={0}
        w="100%" h="100%"
        backgroundImage={`url(${stars})`}
        backgroundRepeat="repeat"
        backgroundSize="contain"
        animation="moveStars 30s linear infinite"
        zIndex={-2}
      />

      {/* planet & satellite */}
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

      {/* station & astronaut */}
      <Image
        src={station}
        alt="Space Station"
        pos="absolute" top="300px" right="20px"
        boxSize="220px"
        animation="float 6s ease-in-out infinite"
      />
      <Image
        src={astronaut}
        alt="Astronaut"
        pos="absolute" top="450px" right="60px"
        boxSize="80px"
        animation="floatFast 4s ease-in-out infinite"
      />

      {/* main */}
      <Container centerContent pt={8} zIndex={1}>
        <Header />

        {/* categories */}
        <HStack spacing={2} wrap="nowrap" overflowX="auto" mb={8}>
          {categories.map(cat => (
            <Button
              key={cat}
              size="sm"
              minW="max-content"
              bg={selectedCategory === cat ? 'purple.600' : 'purple.400'}
              _hover={{ bg: selectedCategory === cat ? 'purple.700' : 'purple.500' }}
              onClick={() => handleCategoryClick(cat)}
              opacity={0.85}
              borderRadius="full"
            >
              {cat}
            </Button>
          ))}
        </HStack>

        <Heading size="lg" mb={4}>
          Latest News {selectedCategory && `(Category: ${selectedCategory})`}
        </Heading>

        {/* news list */}
        <Stack spacing={6} w="100%" align="center">
          {newsItems.map(item => (
            <NewsCard
              key={item.id}
              title={item.title}
              description={item.categories.join(', ')}
              link={item.link}
            />
          ))}
        </Stack>

        {/* pagination with first/last */}
        <HStack mt={6} spacing={2} justify="center">
          <Button
            size="sm"
            w="32px" h="32px"
            disabled={currentPage === 1}
            onClick={() => setCurrentPage(1)}
          >
            1
          </Button>

          {pageWindow[0] > 2 && <Box px={2}>…</Box>}

          {pageWindow.map(p => (
            <Button
              key={p}
              size="sm"
              w="32px" h="32px"
              bg={currentPage === p ? 'purple.600' : 'transparent'}
              color={currentPage === p ? 'white' : 'purple.300'}
              _hover={{ bg: currentPage === p ? 'purple.700' : 'purple.500', color: 'white' }}
              onClick={() => setCurrentPage(p)}
            >
              {p}
            </Button>
          ))}

          {pageWindow[pageWindow.length - 1] < totalPages - 1 && <Box px={2}>…</Box>}

          <Button
            size="sm"
            w="32px" h="32px"
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage(totalPages)}
          >
            {totalPages}
          </Button>
        </HStack>
      </Container>
    </Box>
  );
}
