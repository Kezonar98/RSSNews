import astronaut from '../assets/austronaut.png';
import station from '../assets/cosmicstation.png';
import planet from '../assets/planet1.png';

export const decorations = [
  {
    src: planet,
    alt: 'Planet',
    style: {
      position: 'absolute',
      bottom: '10%',
      left: '15%',
      width: '200px',
      height: '200px',
      animation: 'slowSpin 60s linear infinite',
    },
  },
  {
    src: station,
    alt: 'Space Station',
    style: {
      position: 'absolute',
      top: '15%',
      right: '10%',
      width: '250px',
      height: '250px',
      animation: 'float 6s ease-in-out infinite',
    },
  },
  {
    src: astronaut,
    alt: 'Astronaut',
    style: {
      position: 'absolute',
      top: '30%',
      right: '20%',
      width: '100px',
      height: '100px',
      animation: 'floatFast 4s ease-in-out infinite',
    },
  },
];
