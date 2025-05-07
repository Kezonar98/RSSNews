# Use slim Python base image
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for building and newspaper3k support
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc \
      build-essential \
      cmake \
      git \
      libffi-dev \
      libxml2-dev \
      libxslt1-dev \
      libjpeg-dev \
      zlib1g-dev \
      libopenblas-dev \
      libgomp1 \
    && pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

# Copy shared utilities
COPY common ./common

# Copy and install Python requirements
COPY news_api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY news_api ./

# Ensure Python can resolve 'common'
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
