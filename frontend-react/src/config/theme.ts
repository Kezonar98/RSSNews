import { extendTheme } from '@chakra-ui/react';
import { keyframes } from '@emotion/react';


//Animations
const float = keyframes`
  0% { transform: translateY(0px); }
  50% { transform: translateY(-20px); }
  100% { transform: translateY(0px); }
`;

const floatFast = keyframes`
  0% { transform: translateY(0px); }
  50% { transform: translateY(-30px); }
  100% { transform: translateY(0px); }
`;

const slowSpin = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
`;

const orbit = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
`;

export const theme = extendTheme({
  styles: {
    global: {
      'html, body, #root': {
        height: '100%',
      },
      body: {
        margin: 0,
        padding: 0,
        bg: 'linear-gradient(180deg, #2D046E 0%, #15173D 100%)',
        color: 'white',
        overflow: 'hidden',
      },
    },
  },
  keyframes: {
    float,
    floatFast,
    slowSpin,
    orbit,
  },
  layerStyles: {
    float: {
      animation: `${float} 6s ease-in-out infinite`,
    },
    floatFast: {
      animation: `${floatFast} 4s ease-in-out infinite`,
    },
    slowSpin: {
      animation: `${slowSpin} 60s linear infinite`,
    },
    orbit: {
      animation: `${orbit} 20s linear infinite`,
    },
  },
});
