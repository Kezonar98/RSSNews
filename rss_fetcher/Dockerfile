# rss_fetcher/Dockerfile

FROM python:3.10-slim

# 1. Install system dependencies required for parsing and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libxml2-dev libxslt1-dev libjpeg-dev zlib1g-dev gcc python3-pip \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Copy shared utilities (common module)
COPY common ./common

# 4. Install Python dependencies
COPY rss_fetcher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy application code
COPY rss_fetcher ./

# 6. Ensure Python can import from /app/common
ENV PYTHONPATH=/app

# 7. Default command
CMD ["python", "main.py"]
