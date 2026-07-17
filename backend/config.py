from pathlib import Path
from pydantic_settings import BaseSettings

# Busca el .env en la raíz del proyecto (un nivel arriba de backend/)
ENV_FILE = Path(__file__).parent.parent / ".env"

class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_key: str

    # LLM
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # Firecrawl
    firecrawl_api_key: str = ""

    # Email
    resend_api_key: str = ""
    email_from: str = "alerts@factorypulse.ai"

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"

    # Scheduler
    scheduler_enabled: bool = True
    scheduler_interval_days: int = 7
    scheduler_check_hours: int = 6

    model_config = {
        "env_file": str(ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",   # ignora variables de otros proyectos
    }

settings = Settings()
