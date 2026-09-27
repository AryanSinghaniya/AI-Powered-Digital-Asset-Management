from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    sqlite_db_url: str = Field(default="sqlite:///./data/sqlite.db", env="SQLITE_DB_URL")
    chroma_db_dir: str = Field(default="./data/chroma_db", env="CHROMA_DB_DIR")
    scan_folder: str = Field(default="./sample_media", env="SCAN_FOLDER")
    video_frame_interval_seconds: int = Field(default=5, env="VIDEO_FRAME_INTERVAL_SECONDS")
    clip_model_name: str = Field(default="ViT-B-32", env="CLIP_MODEL_NAME")
    clip_pretrained: str = Field(default="openai", env="CLIP_PRETRAINED")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Deployment & Robustness guards
    demo_mode: bool = Field(default=False, env="DEMO_MODE")
    max_dataset_size_mb: int = Field(default=200, env="MAX_DATASET_SIZE_MB")
    max_files_count: int = Field(default=500, env="MAX_FILES_COUNT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Support for older pydantic behavior
        extra = 'ignore'

settings = Settings()

# Ensure directories exist
os.makedirs(os.path.dirname(settings.sqlite_db_url.replace("sqlite:///", "")), exist_ok=True)
os.makedirs(settings.chroma_db_dir, exist_ok=True)
