"""
Main Application - Wazuh Integration Service
AI-Augmented SOC

FastAPI webhook receiver for Wazuh alerts with AI-powered triage and enrichment.
"""

import asyncio
import uuid

import structlog
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime

from config import get_settings
from models import WazuhAlert, EnrichedAlert
from wazuh_client import WazuhClient
from ai_client import AIClient
from indexer_writer import IndexerEventWriter

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize clients on startup"""
    settings = get_settings()

    # Initialize clients
    app.state.wazuh_client = WazuhClient(settings)
    app.state.ai_client = AIClient(settings)
    app.state.indexer_writer = IndexerEventWriter(settings)
    app.state.settings = settings
    app.state.manual_analysis_jobs = {}
    app.state.manual_analysis_by_alert = {}
    app.state.manual_analysis_semaphore = asyncio.Semaphore(1)

    logger.info(
        "service_startup",
        service=settings.service_name,
        version=settings.service_version,
        min_severity=settings.min_severity,
        rag_threshold=settings.rag_severity_threshold
    )

    yield

    logger.info("service_shutdown")


# FastAPI application
app = FastAPI(
    title="Wazuh Integration Service",
    description="AI-powered webhook receiver for Wazuh alerts with intelligent triage and enrichment",
    version="1.0.0",
    lifespan=lifespan
)


async def _run_manual_analysis(job_id: str, alert: WazuhAlert) -> None:
    """Run one manual analysis job without tying up the dashboard request."""
    job = app.state.manual_analysis_jobs[job_id]
    try:
        async with app.state.manual_analysis_semaphore:
            job["status"] = "running"
            result = await receive_wazuh_alert(alert, force=True)
            job["status"] = "completed"
            job["result"] = result.model_dump(mode="json")
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = getattr(exc, "detail", None) or str(exc)
        logger.error(
            "manual_ollama_analysis_failed",
            alert_id=alert.id,
            job_id=job_id,
            error=job["error"],
        )


@app.post("/manual-analysis", status_code=status.HTTP_202_ACCEPTED)
async def queue_manual_analysis(alert: WazuhAlert):
    """Queue a Threat Hunting event for manual Ollama analysis."""
    existing_id = app.state.manual_analysis_by_alert.get(alert.id)
    existing = app.state.manual_analysis_jobs.get(existing_id)
    if existing and existing["status"] in {"queued", "running", "completed"}:
        return {"job_id": existing_id, "status": existing["status"]}

    job_id = str(uuid.uuid4())
    app.state.manual_analysis_jobs[job_id] = {
        "job_id": job_id,
        "alert_id": alert.id,
        "status": "queued",
        "result": None,
        "error": None,
    }
    app.state.manual_analysis_by_alert[alert.id] = job_id
    asyncio.create_task(_run_manual_analysis(job_id, alert))
    return {"job_id": job_id, "status": "queued"}


@app.get("/manual-analysis/{job_id}")
async def get_manual_analysis(job_id: str):
    """Return the state and eventual result of a manual analysis job."""
    job = app.state.manual_analysis_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Manual analysis job not found")
    return job


@app.post(
    "/webhook",
    response_model=EnrichedAlert,
    status_code=status.HTTP_200_OK,
    summary="Receive and analyze Wazuh alert",
    description="""
    Primary webhook endpoint for Wazuh alert integration.

    Workflow:
    1. Receive Wazuh alert JSON
    2. Transform to Alert Triage format
    3. Call AI Triage service for analysis
    4. If severity >= 8, call RAG service for MITRE enrichment
    5. Return enriched analysis

    Configuration:
    - Minimum severity filter: >= 7 (configurable via MIN_SEVERITY)
    - RAG enrichment threshold: >= 8 (configurable via RAG_SEVERITY_THRESHOLD)
    """
)
async def receive_wazuh_alert(alert: WazuhAlert, force: bool = False):
    """
    Main webhook endpoint: Receive Wazuh alert, analyze with AI, enrich if high severity.

    Args:
        alert: Wazuh alert JSON payload

    Returns:
        EnrichedAlert with AI triage analysis and optional RAG enrichment
    """
    logger.info(
        "webhook_alert_received",
        alert_id=alert.id,
        rule_level=alert.rule.level,
        rule_description=alert.rule.description
    )

    # The Threat Hunting row action can explicitly request analysis for any
    # event. Automatic ingestion still honors the configured severity floor.
    if not force and alert.rule.level < app.state.settings.min_severity:
        logger.info(
            "alert_filtered_low_severity",
            alert_id=alert.id,
            rule_level=alert.rule.level,
            min_severity=app.state.settings.min_severity
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alert severity {alert.rule.level} below minimum threshold {app.state.settings.min_severity}"
        )

    if force:
        logger.info(
            "manual_ollama_analysis_requested",
            alert_id=alert.id,
            rule_level=alert.rule.level,
        )

    try:
        # Step 1: AI Triage Analysis
        ai_client: AIClient = app.state.ai_client
        triage_result = await ai_client.analyze_alert(alert)
        source_ip = ai_client.extract_source_ip(alert)
        dest_ip = ai_client.extract_dest_ip(alert)

        # Step 2: Conditional RAG Enrichment
        rag_result = None
        rag_enrichment_applied = False
        context_parts = []
        kb_refs = []

        if alert.rule.level >= app.state.settings.rag_severity_threshold:
            logger.info(
                "triggering_rag_enrichment",
                alert_id=alert.id,
                rule_level=alert.rule.level
            )

            # Extract MITRE techniques
            mitre_techniques = None
            if alert.rule.mitre:
                mitre_techniques = alert.rule.mitre.get("id")

            rag_result = await ai_client.enrich_with_rag(
                alert_id=alert.id,
                rule_description=alert.rule.description,
                mitre_techniques=mitre_techniques
            )

            if rag_result:
                rag_enrichment_applied = True

        if rag_result and rag_result.get("results"):
            results = rag_result.get("results", [])
            # Extract MITRE context from top results
            for r in results[:3]:  # Top 3 results
                if r.get("document"):
                    context_parts.append(r["document"][:500])  # Truncate long docs
                if r.get("metadata", {}).get("technique_id"):
                    kb_refs.append(r["metadata"]["technique_id"])

        mitre_techniques = ai_client.extract_mitre_techniques(
            alert,
            triage_result=triage_result,
            kb_references=kb_refs,
        )
        mitre_tactics = ai_client.extract_mitre_tactics(alert, triage_result=triage_result)

        # Step 3: Build enriched response
        enriched_alert = EnrichedAlert(
            wazuh_alert_id=alert.id,
            wazuh_rule_level=alert.rule.level,
            wazuh_rule_description=alert.rule.description,
            source_ip=source_ip,
            dest_ip=dest_ip,
            ai_severity=triage_result["severity"],
            ai_category=triage_result["category"],
            ai_confidence=triage_result["confidence"],
            ai_summary=triage_result["summary"],
            ai_is_true_positive=triage_result["is_true_positive"],
            ai_recommendations=triage_result["recommendations"],
            investigation_priority=triage_result["investigation_priority"],
            mitre_techniques=mitre_techniques,
            mitre_tactics=mitre_tactics,
            mitre_context="\n---\n".join(context_parts) if context_parts else None,
            kb_references=kb_refs if kb_refs else None,
            rag_enrichment_applied=rag_enrichment_applied,
            processing_timestamp=datetime.utcnow()
        )

        # Step 4: Correlate into incident
        try:
            correlation = await ai_client.correlate_alert(
                enriched_alert,
                wazuh_alert=alert,
                triage_result=triage_result,
            )
            if correlation:
                enriched_alert.incident_id = correlation.get("incident_id")
                enriched_alert.incident_is_new = correlation.get("is_new_incident")
                enriched_alert.incident_alert_count = correlation.get("incident_alert_count")
                enriched_alert.kill_chain_stage = correlation.get("kill_chain_stage")
        except Exception as e:
            logger.warning("correlation_failed", error=str(e))

        logger.info(
            "alert_processing_complete",
            alert_id=alert.id,
            ai_severity=enriched_alert.ai_severity,
            is_true_positive=enriched_alert.ai_is_true_positive,
            rag_enriched=rag_enrichment_applied
        )

        # Write to OpenSearch / Wazuh Indexer (required path — awaited)
        await app.state.indexer_writer.write_analysis_event(
            wazuh_alert=alert,
            enriched_alert=enriched_alert,
            rag_result=rag_result,
        )

        # Write to Splunk HEC (best-effort — background task, must not block the pipeline).
        # Architecture: AI enrichment → OpenSearch (required) + Splunk HEC (best-effort).
        # A slow or unavailable Splunk will not increase alert-processing latency.
        def _log_hec_task_exception(task: asyncio.Task) -> None:
            exc = task.exception()
            if exc is not None:
                logger.warning("splunk_hec_background_task_error", error=str(exc))

        hec_task = asyncio.create_task(
            app.state.indexer_writer.write_to_splunk_hec(
                wazuh_alert=alert,
                enriched_alert=enriched_alert,
                rag_result=rag_result,
            )
        )
        hec_task.add_done_callback(_log_hec_task_exception)

        return enriched_alert

    except Exception as e:
        logger.error(
            "alert_processing_failed",
            alert_id=alert.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alert processing failed: {str(e)}"
        )


@app.get(
    "/alerts",
    summary="Fetch recent alerts from Wazuh Manager",
    description="Query Wazuh Manager API for high-severity alerts and return enriched analysis"
)
async def fetch_and_analyze_alerts(
    limit: int = 10,
    min_level: int = None,
    time_range: str = "1h"
):
    """
    Fetch alerts from Wazuh Manager and analyze them.

    Args:
        limit: Maximum number of alerts to fetch (default: 10)
        min_level: Minimum rule level filter (default: from config)
        time_range: Time range for alerts (e.g., "1h", "24h", "7d")

    Returns:
        List of enriched alerts with AI analysis
    """
    try:
        wazuh_client: WazuhClient = app.state.wazuh_client
        ai_client: AIClient = app.state.ai_client

        # Fetch alerts from Wazuh
        raw_alerts = await wazuh_client.get_alerts(
            min_level=min_level,
            limit=limit,
            time_range=time_range
        )

        enriched_alerts = []

        for raw_alert in raw_alerts:
            # Parse into WazuhAlert model
            try:
                wazuh_alert = WazuhAlert(**raw_alert)

                # Analyze with AI
                triage_result = await ai_client.analyze_alert(wazuh_alert)

                # Conditional RAG enrichment
                rag_enrichment_applied = False
                rag_result = None

                if wazuh_alert.rule.level >= app.state.settings.rag_severity_threshold:
                    mitre_techniques = None
                    if wazuh_alert.rule.mitre:
                        mitre_techniques = wazuh_alert.rule.mitre.get("id")

                    rag_result = await ai_client.enrich_with_rag(
                        alert_id=wazuh_alert.id,
                        rule_description=wazuh_alert.rule.description,
                        mitre_techniques=mitre_techniques
                    )
                    if rag_result:
                        rag_enrichment_applied = True

                # Build enriched response
                enriched_alert = {
                    "wazuh_alert_id": wazuh_alert.id,
                    "wazuh_rule_level": wazuh_alert.rule.level,
                    "wazuh_rule_description": wazuh_alert.rule.description,
                    "source_ip": ai_client.extract_source_ip(wazuh_alert),
                    "dest_ip": ai_client.extract_dest_ip(wazuh_alert),
                    "mitre_techniques": ai_client.extract_mitre_techniques(
                        wazuh_alert,
                        triage_result=triage_result,
                    ),
                    "mitre_tactics": ai_client.extract_mitre_tactics(
                        wazuh_alert,
                        triage_result=triage_result,
                    ),
                    "ai_analysis": triage_result,
                    "rag_enrichment": rag_result if rag_enrichment_applied else None,
                    "processing_timestamp": datetime.utcnow().isoformat()
                }

                enriched_alerts.append(enriched_alert)

            except Exception as e:
                logger.error(
                    "alert_parsing_failed",
                    alert=raw_alert,
                    error=str(e)
                )
                continue

        return {
            "total_fetched": len(raw_alerts),
            "total_analyzed": len(enriched_alerts),
            "time_range": time_range,
            "alerts": enriched_alerts
        }

    except Exception as e:
        logger.error("fetch_alerts_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch alerts: {str(e)}"
        )


@app.get(
    "/health",
    summary="Service health check",
    description="Check health of Wazuh Integration service and dependencies"
)
async def health_check():
    """
    Health check endpoint with dependency status.

    Returns:
        Service health status and dependency connectivity
    """
    settings = get_settings()
    wazuh_client: WazuhClient = app.state.wazuh_client
    ai_client: AIClient = app.state.ai_client

    async def bounded_check(coro, timeout: float = 4.0) -> bool:
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except Exception as exc:
            logger.warning("dependency_health_check_timeout", error=str(exc))
            return False

    # Check dependencies concurrently. Wazuh Manager can be slow, but the health
    # endpoint must return before Docker's healthcheck timeout.
    wazuh_healthy, triage_healthy, rag_healthy = await asyncio.gather(
        bounded_check(wazuh_client.health_check()),
        bounded_check(ai_client.health_check_triage()),
        bounded_check(ai_client.health_check_rag()),
    )

    overall_status = "healthy" if (wazuh_healthy and triage_healthy) else "degraded"

    return {
        "status": overall_status,
        "service": settings.service_name,
        "version": settings.service_version,
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {
            "wazuh_manager": wazuh_healthy,
            "alert_triage": triage_healthy,
            "rag_service": rag_healthy  # Optional dependency
        },
        "configuration": {
            "min_severity": settings.min_severity,
            "rag_threshold": settings.rag_severity_threshold,
            "indexer_events_enabled": settings.indexer_events_enabled,
            "indexer_event_index_prefix": settings.indexer_event_index_prefix,
        }
    }


@app.post(
    "/events/test",
    summary="Write a demo Aegis Guard event to Wazuh Indexer",
    description="Creates a synthetic Aegis Guard analysis event in ai-soc-events-* for dashboard/demo verification."
)
async def write_test_event():
    """Write a synthetic Aegis Guard event to the Wazuh Indexer."""
    alert = WazuhAlert(
        timestamp=datetime.utcnow().isoformat(),
        id=f"demo-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        rule={
            "level": 10,
            "description": "Demo SSH brute force attack detected",
            "id": "5710",
            "mitre": {
                "id": ["T1110.001"],
                "tactic": ["credential-access"],
                "technique": ["Password Guessing"],
            },
            "groups": ["authentication_failed", "ai_soc_demo"],
        },
        agent={"id": "000", "name": "demo-host", "ip": "10.0.1.50"},
        data={"srcip": "203.0.113.42", "dstip": "10.0.1.50", "dstport": 22, "srcuser": "root"},
        full_log="Failed password for root from 203.0.113.42 port 45678 ssh2",
        location="ai-soc-demo",
    )
    enriched = EnrichedAlert(
        wazuh_alert_id=alert.id,
        wazuh_rule_level=alert.rule.level,
        wazuh_rule_description=alert.rule.description,
        source_ip="203.0.113.42",
        dest_ip="10.0.1.50",
        ai_severity="high",
        ai_category="intrusion_attempt",
        ai_confidence=0.92,
        ai_summary="Demo SSH brute-force activity from 203.0.113.42 against root login.",
        ai_is_true_positive=True,
        ai_recommendations=[
            {
                "action": "Block source IP at the perimeter firewall",
                "priority": 1,
                "rationale": "Prevents continued brute-force attempts from the same source",
            }
        ],
        mitre_techniques=["T1110.001"],
        mitre_tactics=["credential-access"],
        investigation_priority=1,
        rag_enrichment_applied=True,
        kb_references=["T1110.001"],
        incident_id="INC-DEMO-WAZUH-EVENT",
        incident_is_new=True,
        incident_alert_count=1,
        kill_chain_stage="credential_access",
    )

    written = await app.state.indexer_writer.write_analysis_event(alert, enriched)
    if not written:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to write demo Aegis Guard event to Wazuh Indexer",
        )
    return {
        "status": "written",
        "index_pattern": f"{app.state.settings.indexer_event_index_prefix}-*",
        "alert_id": enriched.wazuh_alert_id,
        "incident_id": enriched.incident_id,
    }


@app.get("/", summary="Service information")
async def root():
    """Root endpoint with service information"""
    settings = get_settings()
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "description": "Wazuh-AI Integration: Intelligent alert triage and enrichment",
        "endpoints": {
            "webhook": "/webhook (POST)",
            "alerts": "/alerts (GET)",
            "health": "/health (GET)",
            "docs": "/docs (GET)"
        }
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=True  # Enable for development
    )
