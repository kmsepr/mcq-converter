# Use a lightweight Python base image
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies: ffmpeg and wget (for yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Expose the Flask app port
EXPOSE 3000

# Default command to run the Flask app
CMD ["python", "app.py"]
