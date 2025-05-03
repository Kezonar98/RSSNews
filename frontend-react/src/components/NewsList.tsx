import { useState, useEffect } from 'react';
import {
  Box,
  Select,
  Text,
  Heading,
  Spinner,
  VStack,
  Center,
} from '@chakra-ui/react';
import NewsCard from './NewsCard';
import { fetchNews, fetchCategories, NewsItem } from '../services/api';

export default function NewsList() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    (async () => {
      try {
        const cats = await fetchCategories();
        setCategories(cats);
      } catch (err) {
        console.error('Error fetching categories:', err);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const { items } = await fetchNews(1, 10, selectedCategory || undefined);
        setNews(items);
      } catch (err) {
        console.error('Error fetching news:', err);
      } finally {
        setLoading(false);
      }
    })();
  }, [selectedCategory]);

  return (
    <Box my={8}>
      <Heading size="lg" mb={4} color="white" textAlign="center">
        Select category
      </Heading>

      <Center mb={6}>
        <Select
          placeholder="All categories"
          w="250px"
          value={selectedCategory}
          onChange={e => setSelectedCategory(e.target.value)}
        >
          {categories.map(cat => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </Select>
      </Center>

      {loading ? (
        <Center>
          <Spinner size="xl" />
        </Center>
      ) : news.length > 0 ? (
        <VStack spacing={8}>
          {news.map(item => (
            <NewsCard
              id ={item.id}
              title={item.title}
              description={item.description}
              link={item.link}
            />
          ))}
        </VStack>
      ) : (
        <Text color="white" textAlign="center">
          No news found.
        </Text>
      )}
    </Box>
  );
}
