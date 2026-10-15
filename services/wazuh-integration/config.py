"""
Configuration - Wazuh Integration Service
AI-Augmented SOC

Environment-based configuration for Wazuh API and AI service integration.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Service Identity
    service_name: str = "wazuh-integration"
    service_version: str = "1.0.0"

    # Wazuh Manager Configuration
    wazuh_manager_url: str = "https://wazuh-manager:55000"
    wazuh_username: str = "wazuh-wui"
    wazuh_password: str = Field(
        validation_alias=AliasChoices("wazuh_password", "WAZUH_PASSWORD", "API_PASSWORD")
    )
    wazuh_verify_ssl: bool = False  # Self-signed cert

    # Wazuh Indexer / OpenSearch write-back for demo-visible AI events.
    # These events appear under ai-soc-events-* in Wazuh Dashboard/OpenSearch Discover.
    indexer_url: str = "https://wazuh-indexer:9200"
    indexer_username: str = "admin"
    indexer_password: str = ""
    indexer_verify_ssl: bool = False
    indexer_events_enabled: bool = True
    indexer_event_index_prefix: str = "ai-soc-events"

    # Wazuh Alert Filtering
    min_severity: int = 7  # Minimum rule_level to process (7-15 = high priority)
    max_alerts_per_request: int = 100

    # AI Service Endpoints
    alert_triage_url: str = "http://alert-triage:8000"
    rag_service_url: str = "http://rag-service:8000"
    correlation_engine_url: str = "http://correlation-engine:8000"

    # RAG Enrichment Threshold
    rag_severity_threshold: int = 8  # Only enrich alerts with severity >= 8

    # API Configuration
    host: str = "0.0.0.0"
    port: int = 8002
    log_level: str = "info"

    # Splunk HEC Integration
    splunk_hec_url: str = "http://splunk:8088/services/collector/event"
    splunk_hec_token: str = "CHANGE_ME_SPLUNK_HEC_TOKEN"
    splunk_hec_enabled: bool = True
    splunk_hec_timeout: float = 5.0

    # Timeouts
    wazuh_api_timeout: int = 30
    ai_service_timeout: int = 240

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()
