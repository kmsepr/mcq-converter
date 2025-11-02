# ==============================================================
# 🐍 Base image
# ==============================================================
FROM python:3.11-slim

# --------------------------------------------------------------
# 🧩 Install system dependencies (ffmpeg + yt-dlp prerequisites)
# --------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg wget curl git \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------
# 🧰 Install Python dependencies
# --------------------------------------------------------------
WORKDIR /app

# Copy requirement libraries (you can also use requirements.txt)
RUN pip install --no-cache-dir flask pandas openpyxl yt-dlp

# --------------------------------------------------------------
# 🧱 Copy app files
# --------------------------------------------------------------
COPY app.py /app/app.py

# --------------------------------------------------------------
# 🔧 Environment setup
# --------------------------------------------------------------
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Create /mnt/data for logs and cache (Koyeb uses ephemeral filesystem)
RUN mkdir -p /mnt/data

# --------------------------------------------------------------
# 🚀 Start server
# --------------------------------------------------------------
EXPOSE 8000
CMD ["python", "app.py"]
