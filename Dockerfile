# Base image
FROM --platform=linux/arm64 python:3.9-slim

# Set environment variables for better Python behavior
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies and cleanup in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    tar \
    xz-utils \
    fonts-liberation \
    fontconfig \
    build-essential \
    pkg-config \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Set environment variables for optimization
ENV OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    NUMEXPR_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    VECLIB_MAXIMUM_THREADS=2 \
    GOTO_NUM_THREADS=2 \
    WHISPER_IMPLEMENTATION=FASTER_WHISPER \
    CFLAGS="-O3 -march=armv8.2-a -mcpu=neoverse-n1" \
    CXXFLAGS="-O3 -march=armv8.2-a -mcpu=neoverse-n1" \
    WHISPER_CACHE_DIR="/app/whisper_cache"

# Create cache directory and set up user
RUN mkdir -p ${WHISPER_CACHE_DIR} && \
    useradd -m appuser && \
    chown -R appuser:appuser /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER appuser

# Copy the rest of the application code
COPY --chown=appuser:appuser . .

# Download the model in a separate layer
RUN python -c "from faster_whisper import download_model; download_model('base')"

# Set default command
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "3", "--timeout", "300", "app:app"]