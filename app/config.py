"""Reads settings from environment variables (and from the .env file)."""
import os

from dotenv import load_dotenv

load_dotenv()  # loads values from a file named ".env" if it exists


class Settings:
    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "development")
        self.secret_key = os.getenv("SECRET_KEY", "MS2ypmOZI4qbbXcp6Q4wnsvYWKo1mpBVlucSZiz9jlU")
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./launchforge.db")
        self.ai_mode = os.getenv("AI_MODE", "mock").lower()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.generate_limit = int(os.getenv("GENERATE_LIMIT_PER_HOUR", "10"))

    @property
    def is_prod(self) -> bool:
        return self.app_env == "production"

    def validate(self) -> None:
        """Stop early with a clear message if the setup is unsafe or wrong."""
        if self.ai_mode not in ("mock", "gemini"):
            raise RuntimeError("AI_MODE must be 'mock' or 'gemini'")
        if self.is_prod and self.secret_key == "MS2ypmOZI4qbbXcp6Q4wnsvYWKo1mpBVlucSZiz9jlU":
            raise RuntimeError("Set a real SECRET_KEY in production")


settings = Settings()
settings.validate()
