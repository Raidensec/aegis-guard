"""
Unit tests for Wazuh event context handoff into correlation/response planning.

These tests keep the Ollama-backed response loop honest: the webhook must pass
the source, destination, and MITRE context needed by the correlation engine and
response orchestrator to generate useful defense plans.
"""

import os
import sys
import types

import pytest


SERVICE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "services",
        "wazuh-integration",
    )
)


@pytest.fixture(autouse=True)
def cleanup_wazuh_modules():
    yield
    for module_name in ("config", "models", "ai_client"):
        module = sys.modules.get(module_name)
        module_file = getattr(module, "__file__", "") if module else ""
        if module and "wazuh-integration" in module_file:
            del sys.modules[module_name]


def _load_wazuh_modules():
    if sys.path[0] != SERVICE_PATH:
        sys.path.insert(0, SERVICE_PATH)
    if "structlog" not in sys.modules:
        fake_structlog = types.SimpleNamespace(
            get_logger=lambda: types.SimpleNamespace(
                info=lambda *args, **kwargs: None,
                warning=lambda *args, **kwargs: None,
                error=lambda *args, **kwargs: None,
            )
        )
        sys.modules["structlog"] = fake_structlog
    for module_name in ("config", "models", "ai_client"):
        module = sys.modules.get(module_name)
        module_file = getattr(module, "__file__", "") if module else ""
        if module and "wazuh-integration" not in module_file:
            del sys.modules[module_name]

    import ai_client as ai_client_module
    from ai_client import AIClient
    from config import Settings
    from models import EnrichedAlert, WazuhAlert

    return ai_client_module, AIClient, Settings, EnrichedAlert, WazuhAlert


@pytest.fixture
def wazuh_alert():
    _, _, _, _, WazuhAlert = _load_wazuh_modules()
    return WazuhAlert(
        timestamp="2026-06-17T12:00:00Z",
        id="wazuh-001",
        rule={
            "level": 10,
            "description": "Multiple failed SSH login attempts",
            "id": "5710",
            "mitre": {
                "id": ["T1110"],
                "tactic": ["Credential Access"],
                "technique": ["Brute Force"],
            },
        },
        agent={"id": "001", "name": "web-01", "ip": "10.0.0.50"},
        data={"srcip": "203.0.113.42", "dstip": "10.0.0.50", "dstport": 22},
        full_log="Failed password for root from 203.0.113.42 port 45678 ssh2",
    )


def _settings(Settings):
    return Settings(
        wazuh_password="test",
        alert_triage_url="http://alert-triage:8000",
        rag_service_url="http://rag-service:8000",
        correlation_engine_url="http://correlation-engine:8000",
    )


def test_triage_payload_preserves_event_response_context(wazuh_alert):
    _, AIClient, Settings, _, _ = _load_wazuh_modules()
    client = AIClient(_settings(Settings))

    payload = client.transform_wazuh_to_triage_format(wazuh_alert)

    assert payload["source_ip"] == "203.0.113.42"
    assert payload["dest_ip"] == "10.0.0.50"
    assert payload["mitre_technique"] == ["T1110"]
    assert payload["mitre_tactic"] == ["credential-access"]


@pytest.mark.asyncio
async def test_correlation_payload_feeds_response_orchestrator_context(monkeypatch, wazuh_alert):
    ai_client_module, AIClient, Settings, EnrichedAlert, _ = _load_wazuh_modules()
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "incident_id": "INC-001",
                "is_new_incident": True,
                "correlation_score": 1.0,
                "kill_chain_stage": "privilege_escalation",
                "incident_alert_count": 1,
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(ai_client_module.httpx, "AsyncClient", FakeAsyncClient)

    client = AIClient(_settings(Settings))
    enriched = EnrichedAlert(
        wazuh_alert_id="wazuh-001",
        wazuh_rule_level=10,
        wazuh_rule_description="Multiple failed SSH login attempts",
        ai_severity="high",
        ai_category="intrusion_attempt",
        ai_confidence=0.92,
        ai_summary="SSH brute-force activity detected",
        ai_is_true_positive=True,
        ai_recommendations=[],
        investigation_priority=1,
        kb_references=["T1110.001"],
    )
    triage_result = {
        "mitre_techniques": ["T1110.001"],
        "mitre_tactics": ["Credential Access"],
    }

    result = await client.correlate_alert(
        enriched,
        wazuh_alert=wazuh_alert,
        triage_result=triage_result,
    )

    assert result["incident_id"] == "INC-001"
    assert captured["url"] == "http://correlation-engine:8000/correlate"
    assert captured["json"]["source_ip"] == "203.0.113.42"
    assert captured["json"]["dest_ip"] == "10.0.0.50"
    assert captured["json"]["mitre_techniques"] == ["T1110.001", "T1110"]
    assert captured["json"]["mitre_tactics"] == ["credential-access"]
