from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    redis_url: str = "redis://localhost:6379/0"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    whisper_model: str = "medium"
    tmp_dir: str = "C:/tmp/clipos"

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure tmp dir exists
Path(settings.tmp_dir).mkdir(parents=True, exist_ok=True)