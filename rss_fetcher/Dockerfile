FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install pip and clean up
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirement list and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code into the container
COPY . .

# Set the default command to run the RSS fetcher
CMD ["python", "main.py"]
