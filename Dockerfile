# ==============================================================
# 🐍 Base image
# ==============================================================
FROM python:3.11-slim

# --------------------------------------------------------------
# 🧩 Install system dependencies (ffmpeg + yt-dlp prerequisites)
# --------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg wget curl git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------
# 🧰 Install Python dependencies
# --------------------------------------------------------------
WORKDIR /app

# Copy requirements first for Docker cache optimization
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------------
# 🧱 Copy app files
# --------------------------------------------------------------
COPY app.py .

# --------------------------------------------------------------
# 🔧 Environment setup
# --------------------------------------------------------------
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PATH="/usr/local/bin:$PATH"

# Create /mnt/data for logs and cache
RUN mkdir -p /mnt/data

# --------------------------------------------------------------
# 🧪 Verify ffmpeg installation
# --------------------------------------------------------------
RUN ffmpeg -version && yt-dlp --version

# --------------------------------------------------------------
# 🚀 Start server
# --------------------------------------------------------------
EXPOSE 8000
CMD ["python", "app.py"]
