// src/components/BackgroundDecorations.tsx
import { Box, Image } from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { motion } from 'framer-motion';
import stars from '../assets/stars.png';
import planet from '../assets/planet1.png';
import satellite from '../assets/satellite.png';
import station from '../assets/cosmicstation.png';
import astronaut from '../assets/austronaut.png';

const MotionBox = motion(Box);

// Define animations here
const moveStars = keyframes`
  from { background-position: 0 0; }
  to   { background-position: 0 -500px; }
`;

const spin = keyframes`
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
`;

const float = keyframes`
  0%   { transform: translateY(0px); }
  50%  { transform: translateY(-20px); }
  100% { transform: translateY(0px); }
`;

const floatFast = keyframes`
  0%   { transform: translateY(0px); }
  50%  { transform: translateY(-30px); }
  100% { transform: translateY(0px); }
`;

export default function BackgroundDecorations() {
  return (
    <>
      {/* Background Stars */}
      <Box
         pos="fixed"
         inset={0}  
         w="100%"
         backgroundImage={`url(${stars})`}
         backgroundRepeat="repeat"
         backgroundSize="contain"
         sx={{ animation: `${moveStars} 30s linear infinite` }}
         zIndex={-2}
       />

      {/* Planet with orbiting satellite */}
      <Box
        pos="absolute"
        top="20px"
        left="20px"
        w="180px"
        h="180px"
        sx={{ animation: `${spin} 60s linear infinite` }}
      >
        <Image src={planet} alt="Planet" w="100%" h="100%" objectFit="contain" />
        <MotionBox
          pos="absolute"
          top="90px"
          left="90px"
          w="220px"
          h="220px"
          ml="-110px"
          mt="-110px"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 20, ease: 'linear' }}
          transformOrigin="center"
        >
          <Image
            src={satellite}
            alt="Satellite"
            pos="absolute"
            top="0"
            left="50%"
            transform="translateX(-50%)"
            boxSize="40px"
          />
        </MotionBox>
      </Box>

      {/* Space station */}
      <Image
        src={station}
        alt="Space Station"
        pos="absolute"
        top="500px"
        right="20px"
        boxSize="220px"
        sx={{ animation: `${float} 6s ease-in-out infinite` }}
      />

      {/* Astronaut */}
      <Image
        src={astronaut}
        alt="Astronaut"
        pos="absolute"
        top="600px"
        right="100px"
        boxSize="80px"
        sx={{ animation: `${floatFast} 4s ease-in-out infinite` }}
      />
    </>
  );
}
