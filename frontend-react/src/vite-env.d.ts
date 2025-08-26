/// <reference types="vite/client" />

declare module '*.png' {
  const value: string;
  export default value;
}

declare module '*.svg' {
  const value: string;
  export default value;
}

interface ImportMetaEnv {
  readonly VITE_NEWS_API_URL: string;
  readonly VITE_CATEGORIES_API_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
