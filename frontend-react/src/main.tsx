// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ChakraProvider } from '@chakra-ui/react';
import { HelmetProvider } from 'react-helmet-async'; // SEO provider
import App from './App';
import { theme } from './config/theme';

ReactDOM.createRoot(document.getElementById('root')!).render(

    <HelmetProvider>
      <ChakraProvider theme={theme}>
        <App />
      </ChakraProvider>
    </HelmetProvider>

);
