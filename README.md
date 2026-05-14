# 📰 RSSNews: AI-Powered News Aggregator

An intelligent, microservice-based news aggregation platform that fetches RSS feeds, filters content using a local LLM (Llama-3.2-3B), and serves a clean, rewritten news feed via FastAPI and a React frontend.

## 🚀 Tech Stack
* **Backend:** Python, FastAPI
* **AI / NLP:** Llama-3.2-3B, LangChain (Local Inference)
* **Database:** MongoDB
* **Frontend:** React, TypeScript, Vite
* **Infrastructure:** Docker, Docker Compose

## 🏗️ System Architecture (Microservices)
The platform is built strictly on microservice architecture principles for scalability and isolation:
1. `rss_fetcher`: Background worker that actively parses incoming RSS XML feeds from multiple sources.
2. `moderation_service`: The AI core. It uses prompt engineering and LLMs to analyze, moderate, and rewrite news content to prevent toxicity and enforce formatting rules.
3. `news_api`: The central FastAPI gateway connecting the database to the frontend.
4. `frontend-react`: A modern, responsive user interface built with React and Vite.

## 🛠️ Quick Start (Running Locally)

To deploy the entire ecosystem locally using Docker:

1. Clone the repository:
   ```bash
   git clone [https://github.com/Kezonar98/RSSNews.git](https://github.com/Kezonar98/RSSNews.git)
   cd RSSNews
2. Setup Environment Variables:
```bash
cp .env.example .env
(Ensure you configure the LLAMA_MODEL_PATH in the .env file to point to your local GGUF model).
```
3. Build and launch services:
```bash
docker-compose up -d --build
```
Access the application:

Frontend UI: http://localhost:5173

Backend API Docs: http://localhost:8000/docs

## 🔒 Code Quality & Standards

Security: Sensitive environment variables are excluded from version control (.env.example provided).

Testing: Integrated unit and integration tests (pytest) located in the moderation service.
***
