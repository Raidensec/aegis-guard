"""
AI Client - Wazuh Integration Service
AI-Augmented SOC

Handles communication with Alert Triage and RAG services.
"""

import httpx
import structlog
from collections.abc import Iterable
from typing import Dict, Any, Optional, List
from config import Settings
from models import WazuhAlert

logger = structlog.get_logger()


class AIClient:
    """Client for AI service integration"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.triage_url = settings.alert_triage_url
        self.rag_url = settings.rag_service_url
        self.correlation_url = settings.correlation_engine_url
        self.ai_timeout = settings.ai_service_timeout

        logger.info(
            "ai_client_initialized",
            triage_url=self.triage_url,
            rag_url=self.rag_url,
            correlation_url=self.correlation_url,
        )

    @staticmethod
    def _as_list(value: Any) -> List[str]:
        """Return a de-duplicated list of non-empty strings."""
        if value is None:
            return []
        if isinstance(value, str):
            items: Iterable[Any] = [value]
        elif isinstance(value, Iterable):
            items = value
        else:
            items = [value]

        cleaned = []
        seen = set()
        for item in items:
            if item is None:
                continue
            text = str(item).strip()
            if not text or text in seen:
                continue
            cleaned.append(text)
            seen.add(text)
        return cleaned

    @staticmethod
    def _normalize_tactic(tactic: str) -> str:
        """Normalize MITRE tactic names to the correlation engine's format."""
        return tactic.strip().lower().replace(" ", "-").replace("_", "-")

    def extract_source_ip(self, wazuh_alert: WazuhAlert) -> Optional[str]:
        """Extract the best source/attacker IP candidate from a Wazuh alert."""
        if wazuh_alert.data and wazuh_alert.data.srcip:
            return wazuh_alert.data.srcip
        if wazuh_alert.agent and wazuh_alert.agent.ip:
            return wazuh_alert.agent.ip
        return None

    def extract_dest_ip(self, wazuh_alert: WazuhAlert) -> Optional[str]:
        """Extract the best destination/victim IP candidate from a Wazuh alert."""
        if wazuh_alert.data and wazuh_alert.data.dstip:
            return wazuh_alert.data.dstip
        if wazuh_alert.agent and wazuh_alert.agent.ip:
            return wazuh_alert.agent.ip
        return None

    def extract_mitre_techniques(
        self,
        wazuh_alert: WazuhAlert,
        triage_result: Optional[Dict[str, Any]] = None,
        kb_references: Optional[list] = None,
    ) -> List[str]:
        """Merge ATT&CK techniques from Wazuh, Ollama triage, and RAG refs."""
        merged = []
        if triage_result:
            merged.extend(self._as_list(triage_result.get("mitre_techniques")))
            merged.extend(self._as_list(triage_result.get("mitre_technique")))
        if wazuh_alert.rule.mitre:
            merged.extend(self._as_list(wazuh_alert.rule.mitre.get("id")))
        merged.extend(self._as_list(kb_references))
        return self._as_list(merged)

    def extract_mitre_tactics(
        self,
        wazuh_alert: WazuhAlert,
        triage_result: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Merge and normalize ATT&CK tactics for kill-chain correlation."""
        merged = []
        if triage_result:
            merged.extend(self._as_list(triage_result.get("mitre_tactics")))
            merged.extend(self._as_list(triage_result.get("mitre_tactic")))
        if wazuh_alert.rule.mitre:
            merged.extend(self._as_list(wazuh_alert.rule.mitre.get("tactic")))
        return self._as_list(self._normalize_tactic(t) for t in merged)

    def transform_wazuh_to_triage_format(self, wazuh_alert: WazuhAlert) -> Dict[str, Any]:
        """
        Transform Wazuh alert JSON to Alert Triage SecurityAlert format.

        Args:
            wazuh_alert: Parsed Wazuh alert

        Returns:
            Dictionary matching SecurityAlert model from alert-triage service
        """
        # Extract MITRE techniques if present
        mitre_techniques = self.extract_mitre_techniques(wazuh_alert)
        mitre_tactics = self.extract_mitre_tactics(wazuh_alert)

        # Build SecurityAlert payload
        triage_payload = {
            "alert_id": wazuh_alert.id,
            "timestamp": wazuh_alert.timestamp,
            "rule_id": wazuh_alert.rule.id,
            "rule_description": wazuh_alert.rule.description,
            "rule_level": wazuh_alert.rule.level,
            "raw_log": wazuh_alert.full_log,
            "full_log": wazuh_alert.model_dump(),  # Entire Wazuh alert as context
            "mitre_technique": mitre_techniques,
            "mitre_tactic": mitre_tactics,
        }

        # Add agent information if available
        if wazuh_alert.agent:
            triage_payload["source_hostname"] = wazuh_alert.agent.name
            triage_payload["source_ip"] = wazuh_alert.agent.ip

        # Add parsed data fields if available
        if wazuh_alert.data:
            data = wazuh_alert.data
            if data.srcip:
                triage_payload["source_ip"] = data.srcip
            if data.srcport:
                triage_payload["source_port"] = data.srcport
            if data.dstip:
                triage_payload["dest_ip"] = data.dstip
            if data.dstport:
                triage_payload["dest_port"] = data.dstport
            if data.srcuser:
                triage_payload["user"] = data.srcuser
            elif data.dstuser:
                triage_payload["user"] = data.dstuser

        return triage_payload

    async def analyze_alert(self, wazuh_alert: WazuhAlert) -> Dict[str, Any]:
        """
        Send alert to Alert Triage service for AI analysis.

        Args:
            wazuh_alert: Parsed Wazuh alert

        Returns:
            TriageResponse from alert-triage service
        """
        triage_payload = self.transform_wazuh_to_triage_format(wazuh_alert)
        analyze_url = f"{self.triage_url}/analyze"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    analyze_url,
                    json=triage_payload,
                    timeout=self.ai_timeout
                )
                response.raise_for_status()

                triage_result = response.json()

                logger.info(
                    "alert_triage_analysis_complete",
                    alert_id=wazuh_alert.id,
                    severity=triage_result.get("severity"),
                    is_true_positive=triage_result.get("is_true_positive")
                )

                return triage_result

        except httpx.HTTPError as e:
            logger.error(
                "alert_triage_failed",
                error=str(e),
                alert_id=wazuh_alert.id,
                url=analyze_url
            )
            raise

    async def enrich_with_rag(
        self,
        alert_id: str,
        rule_description: str,
        mitre_techniques: Optional[list] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query RAG service for MITRE ATT&CK and incident context.

        Args:
            alert_id: Alert identifier
            rule_description: Wazuh rule description
            mitre_techniques: List of MITRE technique IDs (e.g., ["T1110"])

        Returns:
            RAG enrichment data or None if service unavailable
        """
        # Build RAG query
        query_parts = [rule_description]
        if mitre_techniques:
            query_parts.extend([f"MITRE {t}" for t in mitre_techniques])

        query = " ".join(query_parts)

        rag_url = f"{self.rag_url}/retrieve"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    rag_url,
                    json={
                        "query": query,
                        "collection": "mitre_attack",
                        "top_k": 3,
                        "min_similarity": 0.5
                    },
                    timeout=self.ai_timeout
                )
                response.raise_for_status()

                rag_result = response.json()

                logger.info(
                    "rag_enrichment_complete",
                    alert_id=alert_id,
                    sources_found=len(rag_result.get("results", []))
                )

                return rag_result

        except httpx.HTTPError as e:
            logger.warning(
                "rag_enrichment_failed",
                error=str(e),
                alert_id=alert_id,
                # Don't fail the entire pipeline if RAG is unavailable
            )
            return None

    async def correlate_alert(
        self,
        enriched_alert,
        wazuh_alert: Optional[WazuhAlert] = None,
        triage_result: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Send an enriched alert to the Correlation Engine for incident grouping.

        Args:
            enriched_alert: EnrichedAlert instance after triage and RAG enrichment
            wazuh_alert: Original Wazuh alert, used as a fallback source of IOCs
            triage_result: Raw Ollama triage output, used for MITRE context

        Returns:
            CorrelationResponse dict or None if the service is unavailable
        """
        try:
            source_ip = getattr(enriched_alert, "source_ip", None)
            dest_ip = getattr(enriched_alert, "dest_ip", None)
            mitre_techniques = list(getattr(enriched_alert, "mitre_techniques", []) or [])
            mitre_tactics = list(getattr(enriched_alert, "mitre_tactics", []) or [])

            if wazuh_alert:
                source_ip = source_ip or self.extract_source_ip(wazuh_alert)
                dest_ip = dest_ip or self.extract_dest_ip(wazuh_alert)
                mitre_techniques = self._as_list(
                    mitre_techniques
                    + self.extract_mitre_techniques(
                        wazuh_alert,
                        triage_result=triage_result,
                        kb_references=getattr(enriched_alert, "kb_references", None),
                    )
                )
                mitre_tactics = self._as_list(
                    mitre_tactics
                    + self.extract_mitre_tactics(wazuh_alert, triage_result=triage_result)
                )

            # Build correlation payload from enriched alert fields
            correlation_data = {
                "alert_id": enriched_alert.wazuh_alert_id,
                "source_ip": source_ip,
                "dest_ip": dest_ip,
                "timestamp": enriched_alert.processing_timestamp.isoformat(),
                "severity": enriched_alert.ai_severity,
                "category": enriched_alert.ai_category,
                "mitre_techniques": mitre_techniques,
                "mitre_tactics": mitre_tactics,
                "rule_description": enriched_alert.wazuh_rule_description,
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.correlation_url}/correlate",
                    json=correlation_data,
                )
                response.raise_for_status()

                result = response.json()

                logger.info(
                    "correlation_complete",
                    alert_id=enriched_alert.wazuh_alert_id,
                    incident_id=result.get("incident_id"),
                    is_new=result.get("is_new_incident"),
                    score=result.get("correlation_score"),
                )

                return result

        except Exception as exc:
            logger.warning(
                "correlation_failed",
                alert_id=enriched_alert.wazuh_alert_id,
                error=str(exc),
            )
            return None

    async def health_check_triage(self) -> bool:
        """Check Alert Triage service health"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.triage_url}/health",
                    timeout=5
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error("triage_health_check_failed", error=str(e))
            return False

    async def health_check_rag(self) -> bool:
        """Check RAG service health"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.rag_url}/health",
                    timeout=5
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.warning("rag_health_check_failed", error=str(e))
            return False  # RAG is optional, so don't fail hard
