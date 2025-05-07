FROM python:3.10-slim

# 1) system packages for newspaper3k, llama-cpp-python
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential cmake git \
      libxml2-dev libxslt1-dev libjpeg-dev zlib1g-dev libgomp1 \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared utilities
COPY common ./common

# Install Python deps (including llama-cpp-python)
COPY rss_fetcher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY rss_fetcher ./

# Ensure our package imports work
ENV PYTHONPATH=/app

CMD ["python", "main.py"]
