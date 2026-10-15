"""
Wazuh Indexer event writer.

Writes Aegis Guard analysis results into a dedicated OpenSearch index so they can
be shown during demos from Wazuh Dashboard/OpenSearch Discover.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import structlog

from config import Settings
from models import EnrichedAlert, WazuhAlert

logger = structlog.get_logger()


class IndexerEventWriter:
    """Best-effort writer for Aegis Guard demo events."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.indexer_url.rstrip("/")
        self.username = settings.indexer_username
        self.password = settings.indexer_password
        self.verify_ssl = settings.indexer_verify_ssl
        self.enabled = settings.indexer_events_enabled
        self.index_prefix = settings.indexer_event_index_prefix

    def _index_name(self) -> str:
        today = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        return f"{self.index_prefix}-{today}"

    def _event_document(
        self,
        wazuh_alert: WazuhAlert,
        enriched_alert: EnrichedAlert,
        rag_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        alert_data = wazuh_alert.data.model_dump(exclude_none=True) if wazuh_alert.data else {}
        agent_data = wazuh_alert.agent.model_dump(exclude_none=True) if wazuh_alert.agent else {}
        rule_data = wazuh_alert.rule.model_dump(exclude_none=True)

        return {
            "@timestamp": now,
            # Schema versioning — increment schema_version when field layout changes so
            # Splunk dashboards can filter by format generation without re-indexing.
            "schema_version": "1.0",
            "pipeline": "ai_soc",
            "enrichment_version": "2026.06",
            "event": {
                "module": "ai-soc",
                "dataset": "ai-soc.analysis",
                "kind": "alert",
                "category": ["intrusion_detection"],
                "type": ["info"],
                "action": "ai_triage_completed",
                "outcome": "success",
            },
            "service": {"name": "wazuh-integration", "type": "ai-soc"},
            "wazuh": {
                "alert": {"id": wazuh_alert.id},
                "rule": rule_data,
                "agent": agent_data,
                "data": alert_data,
                "location": wazuh_alert.location,
            },
            "source": {
                "ip": enriched_alert.source_ip or alert_data.get("srcip") or agent_data.get("ip"),
                "port": alert_data.get("srcport"),
                "user": {"name": alert_data.get("srcuser")},
            },
            "destination": {
                "ip": enriched_alert.dest_ip or alert_data.get("dstip"),
                "port": alert_data.get("dstport"),
                "user": {"name": alert_data.get("dstuser")},
            },
            "ai_soc": {
                "alert_id": enriched_alert.wazuh_alert_id,
                "severity": enriched_alert.ai_severity,
                "category": enriched_alert.ai_category,
                "confidence": enriched_alert.ai_confidence,
                "summary": enriched_alert.ai_summary,
                "is_true_positive": enriched_alert.ai_is_true_positive,
                "investigation_priority": enriched_alert.investigation_priority,
                "recommendations": enriched_alert.ai_recommendations,
                "rag_enrichment_applied": enriched_alert.rag_enrichment_applied,
                "mitre_techniques": enriched_alert.mitre_techniques,
                "mitre_tactics": enriched_alert.mitre_tactics,
                "kb_references": enriched_alert.kb_references or [],
                "incident": {
                    "id": enriched_alert.incident_id,
                    "is_new": enriched_alert.incident_is_new,
                    "alert_count": enriched_alert.incident_alert_count,
                    "kill_chain_stage": enriched_alert.kill_chain_stage,
                },
            },
            "rag": {
                "result_count": len((rag_result or {}).get("results", [])),
            },
            "message": (
                f"Aegis Guard {enriched_alert.ai_severity} analysis for Wazuh alert "
                f"{enriched_alert.wazuh_alert_id}: {enriched_alert.ai_summary}"
            ),
        }

    async def write_analysis_event(
        self,
        wazuh_alert: WazuhAlert,
        enriched_alert: EnrichedAlert,
        rag_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Write AI analysis result to Wazuh Indexer. Returns False on failure."""
        if not self.enabled:
            return False

        document = self._event_document(wazuh_alert, enriched_alert, rag_result)
        url = f"{self.base_url}/{self._index_name()}/_doc"

        try:
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=10.0) as client:
                response = await client.post(
                    url,
                    auth=(self.username, self.password),
                    json=document,
                )
                response.raise_for_status()

            logger.info(
                "ai_soc_event_written_to_indexer",
                index=self._index_name(),
                alert_id=enriched_alert.wazuh_alert_id,
                incident_id=enriched_alert.incident_id,
            )
            return True
        except Exception as exc:
            logger.warning(
                "ai_soc_event_write_failed",
                error=str(exc),
                index=self._index_name(),
                alert_id=enriched_alert.wazuh_alert_id,
            )
            return False

    async def write_to_splunk_hec(
        self,
        wazuh_alert: WazuhAlert,
        enriched_alert: EnrichedAlert,
        rag_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Write enriched AI-SOC event to Splunk HTTP Event Collector (HEC).

        Returns True on success, False on any failure (Splunk outages must not
        block the main alert pipeline — all exceptions are caught here).
        """
        if not self.settings.splunk_hec_enabled:
            return False

        document = self._event_document(wazuh_alert, enriched_alert, rag_result)
        headers = {
            "Authorization": f"Splunk {self.settings.splunk_hec_token}",
            "Content-Type": "application/json",
        }
        payload = {"event": document}

        try:
            async with httpx.AsyncClient(timeout=self.settings.splunk_hec_timeout) as client:
                response = await client.post(
                    self.settings.splunk_hec_url, headers=headers, json=payload
                )
                response.raise_for_status()
            logger.info(
                "ai_soc_event_written_to_splunk",
                alert_id=enriched_alert.wazuh_alert_id,
                incident_id=enriched_alert.incident_id,
                hec_status=response.status_code,
            )
            return True
        except httpx.TimeoutException as exc:
            logger.warning(
                "ai_soc_splunk_hec_timeout",
                error=str(exc),
                alert_id=enriched_alert.wazuh_alert_id,
                hint="Splunk may be down or unreachable. Check container health.",
            )
            return False
        except Exception as exc:
            logger.warning(
                "ai_soc_splunk_write_failed",
                error=str(exc),
                alert_id=enriched_alert.wazuh_alert_id,
            )
            return False
