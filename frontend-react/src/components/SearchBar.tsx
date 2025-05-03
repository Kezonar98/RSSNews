import { useState } from 'react';
import {
  Input,
  InputGroup,
  InputRightElement,
  IconButton,
} from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';

interface SearchBarProps {
  onSearch: (query: string) => void;
}

export default function SearchBar({ onSearch }: SearchBarProps) {
  const [value, setValue] = useState('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      onSearch(value.trim());
    }
  };

  return (
    <InputGroup size="md" w="350px" borderRadius="full" overflow="hidden" bg="rgba(30, 10, 70, 0.7)">
      <Input
        placeholder="🔭 Search cosmic news..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        bg="transparent"
        color="white"
        _placeholder={{ color: 'gray.300' }}
        border="none"
        borderRadius="full"
        _focus={{ boxShadow: 'none' }}
      />
      <InputRightElement>
        <IconButton
          aria-label="Search"
          icon={<SearchIcon />}
          size="md"
          borderRadius="full"
          colorScheme="purple"
          onClick={() => onSearch(value.trim())}
        />
      </InputRightElement>
    </InputGroup>
  );
}
