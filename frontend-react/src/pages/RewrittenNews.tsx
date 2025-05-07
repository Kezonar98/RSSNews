import React, { useState, useEffect } from 'react';
import { useParams, Link as RouterLink } from 'react-router-dom';
import { Box, Container, Heading, Text, Spinner, Button, Stack } from '@chakra-ui/react';
import { fetchNewsById } from '../services/api';
import BackgroundDecorations from '../components/BackgroundDecorations';

export default function RewrittenNews() {
  const { id } = useParams<{ id: string }>();
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

  if (loading) return <Spinner size="xl" />;

  if (!item) return <Text>Article not found.</Text>;

  const title = item.rewritten_title?.trim() || item.title;
  const body = item.rewritten_body?.trim() || item.description || 'No content available.';

  return (
    <Box pos="relative" w="100%" minH="100vh">
      {/* Background decorations */}
      <BackgroundDecorations />

      <Container centerContent pt={24} pb={10} zIndex={1}>
        {/* Back button */}
        <Button mb={4} as={RouterLink} to="/" colorScheme="purple">
          ← Back Home
        </Button>

        {/* Title */}
        <Heading size="xl" mb={6} textAlign="center">
          {title}
        </Heading>

        {/* Main news card */}
        <Box
          bg="rgba(0, 0, 0, 0.7)"
          borderRadius="lg"
          boxShadow="xl"
          p={6}
          w="90%"
          maxW="900px"
          mb={6}
        >
          {body.startsWith("[ERROR]") || body.startsWith("[WARNING]") ? (
            <Text color="red.400" mb={4}>⚠️ {body}</Text>
          ) : (
            body.split('\n\n').map((p: string, i: number) => (
              <Text key={i} mb={4}>{p}</Text>
            ))
          )}
        </Box>

        {/* Original source link */}
        <Text mt={10} textAlign="center">
          Original source:{' '}
          <a href={item.link} target="_blank" rel="noopener noreferrer" style={{ color: '#B28BFF' }}>
            {item.link}
          </a>
        </Text>
      </Container>
    </Box>
  );
}
