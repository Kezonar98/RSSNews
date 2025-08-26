FROM cosmicrssnews-base:latest

WORKDIR /app

# Copy shared utilities
COPY common ./common

# Copy app code
COPY news_api ./

# Ensure Python can resolve 'common'
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
