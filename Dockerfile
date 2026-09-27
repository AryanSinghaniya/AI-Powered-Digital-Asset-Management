FROM python:3.10-slim

# Set non-interactive env to avoid prompts during apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (Tesseract for OCR, libgl1 for OpenCV video processing)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download and cache CLIP model during build so it doesn't download on startup
# You can change 'ViT-B-32' to a smaller model if needed via build args, but caching the default here
RUN python -c "\
import open_clip; \
open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai'); \
"

# Copy application code
COPY . /app

# Ensure required directories exist for cold start
RUN mkdir -p /app/data/chroma_db /app/sample_media

EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
