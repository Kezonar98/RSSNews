# news_api/Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Install system deps for potential future use (newspaper3k, etc.) and pip upgrade
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc libffi-dev libxml2-dev libxslt1-dev libjpeg-dev zlib1g-dev \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

# Expose common utilities
COPY common ./common

# Install Python requirements
COPY news_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY news_api ./

# Make sure Python can find the 'common' package
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
