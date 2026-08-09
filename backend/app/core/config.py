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
    decision_policy_reference: str = "DRM-001-default-policy"
    decision_policy_version: str = "DRM-001-v1.1-default"
    decision_high_confidence_threshold: float = Field(default=0.9, ge=0, le=1)
    decision_medium_confidence_threshold: float = Field(default=0.65, ge=0, le=1)
    governance_policy_reference: str = "GOV-POL-DEFAULT"
    governance_policy_version: str = "1.0"
    governance_authorized_exception_authorities: list[str] = Field(default_factory=list)
    governance_high_confidence_threshold: float = Field(default=0.9, ge=0, le=1)
    governance_medium_confidence_threshold: float = Field(default=0.65, ge=0, le=1)
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    oidc_subject_claim: str = "sub"
    oidc_tenant_claim: str = "tenant_id"
    oidc_scope_claim: str = "scope"
    oidc_roles_claim: str = "roles"
    oidc_clock_skew_seconds: int = Field(default=60, ge=0, le=300)
    oidc_jwks_cache_seconds: int = Field(default=300, ge=30, le=3600)
    supplier_risk_payload_limit_bytes: int = Field(default=262_144, ge=1024)
    supplier_risk_rate_limit_per_minute: int = Field(default=60, ge=1)
    runtime_handoff_key: str = ""
    runtime_handoff_key_id: str = Field(default="primary", min_length=1, max_length=100)


@lru_cache
def get_settings() -> Settings:
    return Settings()
