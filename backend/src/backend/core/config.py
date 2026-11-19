from pathlib import Path

from pydantic import Field, SecretStr
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
    hf_token: SecretStr = SecretStr("")
    hf_space_url: str = "https://ivannm-qwen-image-edit-2509-loras-fast2-copy.hf.space"
    hf_api_name: str = Field(default="infer", pattern=r"^[A-Za-z0-9_-]+$")
    hf_timeout_seconds: float = Field(default=300.0, gt=0)

    # Comma-separated list of origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Where uploaded and generated images are stored. Relative paths are
    # resolved against the working directory.
    upload_dir: Path = Path("uploads")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ai_configured(self) -> bool:
        return self.hf_token.get_secret_value().strip() not in ("", "replace_me")


settings = Settings()
