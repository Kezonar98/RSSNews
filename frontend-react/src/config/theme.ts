// src/theme/theme.ts
import { extendTheme } from '@chakra-ui/react';

export const theme = extendTheme({
  styles: {
    global: {
      // Box-sizing reset
      '*, *::before, *::after': {
        boxSizing: 'border-box',
      },
      'html, body, #root': {
               minHeight: '100vh',
               height: 'auto',
               margin: 0,
               padding: 0,
             },
      // Body background and text
      body: {
        bg: 'linear-gradient(180deg, #2D046E 0%, #15173D 100%)',
        color: 'white',
        overflowY: 'auto',
        overflowX: 'auto',
      },
      // Prefers-reduced-motion
      '@media (prefers-reduced-motion: reduce)': {
        '*, *::before, *::after': {
          animation: 'none !important',
          transition: 'none !important',
        },
      },
    },
  },
});
