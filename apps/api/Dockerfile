FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies for PostGIS and CV
# (libgl1-mesa-glx no longer exists in current Debian; libgl1 replaces it)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
# CPU-only PyTorch wheels keep the image ~2GB smaller than the default CUDA build
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 5 --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Copy application
COPY . .

# Create models directory
RUN mkdir -p models

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
