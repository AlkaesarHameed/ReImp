# PaddleOCR with English + Arabic support
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PaddlePaddle and PaddleOCR with compatible versions
RUN pip install --no-cache-dir \
    "numpy<2.0.0" \
    paddlepaddle==2.6.2 \
    paddleocr==2.7.3 \
    opencv-python-headless==4.9.0.80 \
    flask>=3.0.0 \
    gunicorn>=21.0.0 \
    Pillow>=9.0.0

# Create app directory
WORKDIR /app

# Copy the server application
COPY server.py /app/server.py

# Note: Models will be downloaded on first use
# Pre-downloading can cause segfaults in some environments

# Expose port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:9090/health || exit 1

# Run the server
CMD ["gunicorn", "--bind", "0.0.0.0:9090", "--workers", "2", "--timeout", "120", "server:app"]
