import uvicorn
import os

# Create necessary directories for Hugging Face Spaces
os.makedirs("./data/chroma_db", exist_ok=True)
os.makedirs("./sample_media", exist_ok=True)

from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
