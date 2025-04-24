// frontend/static/main.js
document.addEventListener("DOMContentLoaded", () => {
  const cfg = window.APP_CONFIG;

  const categoryList = document.getElementById("category-list");
  const container    = document.querySelector(`.${cfg.CONTAINER_CLASS}`);
  let latestNews     = [];
  let selectedCat    = null;
  let visibleCount   = 10;

  // Встановлюємо картинки
  ["planet","satellite","astronaut","station"].forEach(key => {
    const img = document.getElementById(`${key}-img`);
    if (img && cfg.images[key]) img.src = cfg.images[key];
  });

  // Завантажуємо і показуємо тільки MAIN_CATEGORIES
  function loadCategories() {
    categoryList.textContent = "";
    // 1) Додаємо кнопку "All News"
    categoryList.insertAdjacentHTML("beforeend",
      `<li><a href="#/" class="text-white font-bold category-link">All News</a></li>`
    );

    // 2) Only MAIN_CATEGORIES
    cfg.MAIN_CATEGORIES.forEach(cat => {
      categoryList.insertAdjacentHTML("beforeend",
        `<li>
          <a href="#/category/${encodeURIComponent(cat)}"
             class="category-link text-blue-400 hover:text-blue-600">
            ${cat}
          </a>
        </li>`
      );
    });
  }

  // Читаємо хеш, щоб зрозуміти обрану категорію
  function getSelectedCategoryFromURL() {
    const m = window.location.hash.match(/^#\/category\/(.+)$/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  // Малюємо новини, фільтруючи їх по selectedCat
  function renderNews() {
    container.innerHTML = "";
    selectedCat = getSelectedCategoryFromURL();

    const filtered = selectedCat
      ? latestNews.filter(n => (n.categories||[]).includes(selectedCat))
      : latestNews;

    filtered.slice(0, visibleCount).forEach(item => {
      const div = document.createElement("div");
      div.className = cfg.ITEM_CLASS;
      div.innerHTML = cfg.ITEM_TEMPLATE
        .replace(/{{link}}/g,       item.link)
        .replace(/{{title}}/g,      item.title)
        .replace(/{{published}}/g,  item.published || "No date")
        .replace(/{{source}}/g,     item.source)
        .replace(/{{link_class}}/g, cfg.LINK_CLASS)
        .replace(/{{date_class}}/g, cfg.DATE_CLASS)
        .replace(/{{source_class}}/g, cfg.SOURCE_CLASS);
      container.appendChild(div);
      setTimeout(() => div.classList.remove("animate-fade-in-slide"), 600);
    });

    if (filtered.length > visibleCount) {
      const btn = document.createElement("button");
      btn.textContent = "Load more";
      btn.className = "mt-4 px-4 py-2 bg-blue-700 text-white rounded hover:bg-blue-800";
      btn.onclick = () => { visibleCount += 10; renderNews(); };
      container.appendChild(btn);
    }
  }

  // Підтягуємо свіжі новини
  async function fetchNews() {
    try {
      const res = await fetch(`${cfg.API_BASE}${cfg.NEWS_ENDPOINT}`);
      const data = await res.json();
      latestNews = data.sort((a,b) => new Date(b.published) - new Date(a.published));
      visibleCount = 10;
      renderNews();
    } catch (e) {
      console.error("Error fetching news:", e);
    }
  }

  // Клік у сайдбарі
  categoryList.addEventListener("click", e => {
    if (e.target.tagName === "A") {
      e.preventDefault();
      window.location.hash = e.target.getAttribute("href");
    }
  });

  // Слухаємо зміну хешу
  window.addEventListener("hashchange", () => {
    visibleCount = 10;
    renderNews();
  });

  // Ініціалізація
  loadCategories();
  fetchNews();
  setInterval(fetchNews, cfg.REFRESH_INTERVAL);
});
