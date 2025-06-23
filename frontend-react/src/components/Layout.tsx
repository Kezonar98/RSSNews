// src/components/Layout.tsx
import React from 'react';
import { Box, HStack, IconButton } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import { AiFillHome } from 'react-icons/ai';
import SearchBar from './SearchBar';
import BackgroundDecorations from './BackgroundDecorations';

interface LayoutProps {
  onSearch: (query: string) => void;
  children: React.ReactNode;
}

export default function Layout({ onSearch, children }: LayoutProps) {
  const navigate = useNavigate();

  return (
    <Box pos="relative" w="100%" minH="100vh" overflow="hidden">
      {/* Background */}
      <BackgroundDecorations />

      {/* Search + Home */}
      <Box pos="absolute" top="20px" right="20px" zIndex={2}>
        <HStack spacing={2}>
          <SearchBar onSearch={onSearch} />
          <IconButton
            aria-label="Home"
            icon={<AiFillHome />}
            onClick={() => navigate('/')}
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

      {/* Page Content */}
      <Box pos="relative" zIndex={1}>
        {children}
      </Box>
    </Box>
  );
}
