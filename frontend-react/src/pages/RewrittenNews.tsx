// src/pages/RewrittenNews.tsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Heading,
  Text,
  Spinner,
  Stack,
  useBreakpointValue,
} from '@chakra-ui/react';
import { fetchNewsById } from '../services/api';
import Layout from '../components/Layout';
import BackgroundDecorations from '../components/BackgroundDecorations';

export default function RewrittenNews() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Ширина обгортки: від 100% на мобільних до 70% на великих екранах
  const wrapperMaxW = useBreakpointValue({
    base: '100%',
    md: '85%',
    lg: '75%',
    xl: '70%',
  });

  const [item, setItem] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const data = await fetchNewsById(id);
        setItem(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const handleSearch = (q: string) => {
    navigate(`/?search=${encodeURIComponent(q)}`);
  };

  if (loading) {
    return (
      <Layout onSearch={handleSearch}>
        <Spinner size="xl" mt={20} color="purple.400" />
      </Layout>
    );
  }

  if (!item) {
    return (
      <Layout onSearch={handleSearch}>
        <Text mt={20} textAlign="center">
          Article not found.
        </Text>
      </Layout>
    );
  }

  const title = item.rewritten_title?.trim() || item.title;
  const body = item.rewritten_body?.trim() || item.description || 'No content available.';
  const published = new Date(item.published).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <Layout onSearch={handleSearch}>
      <BackgroundDecorations />

      <Container
        pt={24}
        pb={16}
        zIndex={1}
        maxW="container.xl"
        px={{ base: 4, md: 6, lg: 8 }}
      >
        {/* Заголовок */}
        <Stack spacing={2} mb={8} textAlign="center">
          <Heading size="2xl" color="white">
            {title}
          </Heading>
          <Text fontSize="md" color="gray.300">
            {published} • {new URL(item.link).hostname}
          </Text>
        </Stack>

        {/* Основна «картка» статті */}
        <Box
          bg="rgba(0, 0, 20, 0.6)"
          border="2px solid transparent"
          borderRadius="md"
          boxShadow="0 0 30px rgba(138, 43, 226, 0.5)"
          p={{ base: 8, md: 12 }}
          w="100%"
          maxW={wrapperMaxW}
          mx="auto"   /* Центруємо */
          sx={{
            borderImageSlice: 1,
            borderImageSource: 'linear-gradient(to right, #7F00FF, #E100FF)',
          }}
        >
          {body.startsWith('[ERROR]') || body.startsWith('[WARNING]') ? (
            <Text color="red.400" mb={4} fontSize="lg">
              ⚠️ {body}
            </Text>
          ) : (
            body.split('\n\n').map((paragraph: string, idx: number) => (
              <Text
                key={idx}
                mb={8}
                color="white"
                fontSize="xl"
                lineHeight="tall"
                textAlign="justify"
              >
                {paragraph}
              </Text>
            ))
          )}

          <Text mt={8} fontSize="sm" color="gray.400" textAlign="right">
            Source:{' '}
            <a
              href={item.link}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#B28BFF' }}
            >
              {new URL(item.link).hostname}
            </a>
          </Text>
        </Box>
      </Container>
    </Layout>
  );
}
