from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///../data/kg_annotator.db"
    upload_dir: Path = Path("../data/documents")
    ontology_path: Path = Path("../config/ontology.yaml")
    prompt_path: Path = Path("../config/prompts/triple_extraction_v1.jinja2")
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "gpt-4.1-mini"
    bigmodel_api_key: str | None = None
    bigmodel_embedding_url: str = "https://open.bigmodel.cn/api/paas/v4/embeddings"
    embedding_model: str = "embedding-3"
    embedding_dimensions: int = 1024
    embedding_auto_merge_threshold: float = 0.99
    embedding_candidate_threshold: float = 0.85
    extraction_temperature: float = 0.3
    pdf_parser: str = "auto"
    mineru_api_key: str | None = None
    mineru_poll_interval: float = 5
    mineru_poll_timeout: float = 900
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def llm_api_key(self) -> str | None:
        return self.deepseek_api_key or self.openai_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
