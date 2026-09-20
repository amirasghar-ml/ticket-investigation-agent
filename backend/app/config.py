from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    github_token: str = ""
    github_repo: str = "acme/webapp"
    database_url: str = f"sqlite:///{(DATA_DIR / 'support_agent.db').as_posix()}"
    max_tool_iterations: int = 6


settings = Settings()
DATA_DIR.mkdir(parents=True, exist_ok=True)
