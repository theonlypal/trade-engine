from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

GITHUB_REMOTE_URL = "https://github.com/USERNAME/trade-engine.git"
NTFY_TOPIC_URL_EXAMPLE = "https://ntfy.sh/t0ae-rayan-signals-xyz"


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"
    ntfy_topic_url: str
    min_confidence: float = 0.6
    min_expected_move: float = 0.7
    fda_lookback_hours: int = 2

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
