// frontend/static/config.js
window.APP_CONFIG = {
  API_BASE:             "",
  NEWS_ENDPOINT:        "/api/news",
  CATEGORIES_ENDPOINT:  "/api/categories",
  REFRESH_INTERVAL:     60000,
  CONTAINER_CLASS:      "news-container",

  ITEM_CLASS:   "news-item animate-fade-in-slide p-5 border border-blue-500 rounded-lg bg-gray-800 shadow-md w-3/4 mb-4",
  LINK_CLASS:   "text-xl font-semibold text-blue-300 hover:text-blue-500 transition",
  DATE_CLASS:   "text-sm text-gray-400",
  SOURCE_CLASS: "text-xs text-gray-500",

  // Categories
  MAIN_CATEGORIES: [
    "World",
    "Politics",
    "Technology",
    "Science",
    "Health",
    "Games",
    "Anime",
    "Sport",
    "Economy",
    "Culture"
  ],

  ITEM_TEMPLATE: `
    <a href="{{link}}" target="_blank" class="{{link_class}}">
      {{title}}
    </a>
    <p class="{{date_class}}">{{published}}</p>
    <p class="{{source_class}}">Source: {{source}}</p>
  `,

  images: {
    planet:    "/static/planet1.png",
    satellite: "/static/satellite.png",
    astronaut: "/static/austronaut.png",
    station:   "/static/cosmicstation.png"
  }
};
