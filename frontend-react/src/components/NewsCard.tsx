import { Box, Heading, Text, Link } from '@chakra-ui/react';

interface NewsCardProps {
  title: string;
  description: string;
  link: string;
  id: string;
}

export default function NewsCard({ title, description, link }: NewsCardProps) {
  return (
    <Box
      w={{ base: '95vw', md: '800px', lg: '1000px' }} // зберігаємо розмір
      p={6}
      minH="140px"
      shadow="xl"
      borderWidth="1px"
      borderRadius="lg"
      bg="rgba(45, 4, 110, 0.6)"
      _hover={{ bg: 'rgba(45, 4, 110, 0.8)' }}
      transition="background 0.2s"
    >
      <Heading fontSize="2xl" mb={2} color="white">
        {title}
      </Heading>
      <Text mb={4} color="gray.200" noOfLines={3}>
        {description}
      </Text>
      <Link href={link} color="#B28BFF" isExternal fontWeight="bold">
        Read more →
      </Link>
    </Box>
  );
}
