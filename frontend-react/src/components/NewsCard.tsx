// src/components/NewsCard.tsx
import { Box, Heading, Text } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';

interface NewsCardProps {
  id: string;
  title: string;
  description: string;
  slug: string;   // new field for SEO-friendly URLs
}

export default function NewsCard({ id, title, description, slug }: NewsCardProps) {
  return (
    <Box
      w={{ base: '95vw', md: '800px', lg: '1000px' }}
      p={6}
      minH="140px"
      shadow="xl"
      borderWidth="1px"
      borderRadius="lg"
      bg="rgba(45, 4, 110, 0.6)"
      _hover={{ bg: 'rgba(45, 4, 110, 0.8)' }}
      transition="background 0.2s"
    >
      {/* Title */}
      <Heading fontSize="2xl" mb={2} color="white">
        {title}
      </Heading>

      {/* Short description */}
      <Text mb={4} color="gray.200" noOfLines={3}>
        {description}
      </Text>

      {/* SEO-friendly link */}
      <RouterLink 
        to={`/article/${slug}-${id}`} 
        style={{ fontWeight: 'bold', color: '#B28BFF' }}
      >
        Read more →
      </RouterLink>
    </Box>
  );
}
