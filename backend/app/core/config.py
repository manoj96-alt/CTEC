from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="CTEC_", case_sensitive=False, extra="ignore"
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    database_url: str | None = None
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_pool_timeout_seconds: int = Field(default=30, ge=1)
    dataset_archive_path: str = "datasets/edt-001/v3/CTEC_YC_SupplyChain_Dataset_v3.zip"
    resolution_policy_version: str = "ERM-001-v2.1-default"
    resolution_resolved_threshold: float = Field(default=0.9, ge=0, le=1)
    resolution_possible_threshold: float = Field(default=0.65, ge=0, le=1)
    resolution_high_confidence_threshold: float = Field(default=0.9, ge=0, le=1)
    resolution_medium_confidence_threshold: float = Field(default=0.65, ge=0, le=1)
    semantic_policy_version: str = "SRM-001-v2.1-default"
    semantic_resolved_threshold: float = Field(default=0.9, ge=0, le=1)
    semantic_possible_threshold: float = Field(default=0.65, ge=0, le=1)
    semantic_high_confidence_threshold: float = Field(default=0.9, ge=0, le=1)
    semantic_medium_confidence_threshold: float = Field(default=0.65, ge=0, le=1)
    assertion_policy_version: str = "ASM-001-v2.0-default"
    assertion_established_threshold: float = Field(default=0.9, ge=0, le=1)
    assertion_candidate_threshold: float = Field(default=0.65, ge=0, le=1)
    assertion_high_confidence_threshold: float = Field(default=0.9, ge=0, le=1)
    assertion_medium_confidence_threshold: float = Field(default=0.65, ge=0, le=1)
    knowledge_policy_version: str = "KRM-001-v1.2-default"
    knowledge_authorized_acceptance_authorities: list[str] = Field(default_factory=list)
    knowledge_high_confidence_threshold: float = Field(default=0.9, ge=0, le=1)
    knowledge_medium_confidence_threshold: float = Field(default=0.65, ge=0, le=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
