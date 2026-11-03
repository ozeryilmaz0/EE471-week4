# Small Debian-based Python image
FROM python:3.11-slim-bookworm

# System packages: ffmpeg for audio conversion, plus the native libraries the Azure Speech SDK needs
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates libssl3 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# All following commands run inside /app
WORKDIR /app

# Install Python dependencies first so this layer is cached until requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY . .

# Flask listens on this port inside the container
EXPOSE 5000

# Start the Flask app
CMD ["python", "app.py"]
