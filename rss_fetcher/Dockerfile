FROM cosmicrssnews-base:latest

WORKDIR /app

# Copy shared utilities
COPY common ./common

# Copy code
COPY rss_fetcher ./

# Ensure our package imports work
ENV PYTHONPATH=/app

CMD ["python", "main.py"]
