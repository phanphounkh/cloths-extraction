from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str

    # Leave empty to start the API without AI generation configured;
    # /images/extract then answers 503 with a clear message.
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.5-flash-image"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 120.0
    # Optional rendering quality ("low", "medium", "high", "auto"). Only some
    # models accept it (e.g. OpenAI gpt-image); leave empty for the others,
    # which reject unknown parameters. For gpt-image it drives the price.
    openrouter_image_quality: str = ""

    # Which backend generates images: "openrouter" (hosted API) or "kaggle"
    # (a model served over HTTP from a Kaggle notebook GPU; see /kaggle).
    image_backend: Literal["openrouter", "kaggle"] = "openrouter"
    # Public URL printed by the notebook (changes every session) and the
    # shared secret it checks in the Authorization header.
    kaggle_base_url: str = ""
    kaggle_api_token: str = ""
    kaggle_timeout_seconds: float = 300.0

    # Comma-separated list of origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Where uploaded and generated images are stored. Relative paths are
    # resolved against the working directory.
    upload_dir: Path = Path("uploads")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key) and self.openrouter_api_key != "replace_me"

    @property
    def kaggle_configured(self) -> bool:
        return bool(self.kaggle_base_url) and bool(self.kaggle_api_token)

    @property
    def ai_configured(self) -> bool:
        if self.image_backend == "kaggle":
            return self.kaggle_configured
        return self.openrouter_configured


settings = Settings()
