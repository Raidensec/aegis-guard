"""
Aegis Guard Command Center — Dashboard Backend
==========================================
Flask proxy server that forwards requests from the frontend to the
individual Aegis Guard microservices.  The browser only ever talks to
port 5050 (this process), eliminating all CORS friction.

Run with: python dashboard/app.py
Access at: http://localhost:5050
"""

from flask import Flask, render_template, jsonify, request, Response
import subprocess
import json
import os
import requests
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Service registry
# ---------------------------------------------------------------------------
AI_SERVICES = {
    "ml-inference": {
        "url": "http://localhost:8500",
        "label": "ML Inference",
        "description": "Anomaly detection and threat classification",
    },
    "alert-triage": {
        "url": "http://localhost:8100",
        "label": "Alert Triage",
        "description": "LLM-powered alert analysis",
    },
    "rag-service": {
        "url": "http://localhost:8300",
        "label": "RAG Service",
        "description": "Security knowledge base retrieval",
    },
    "wazuh-integration": {
        "url": "http://localhost:8002",
        "label": "Wazuh Integration",
        "description": "SIEM alert forwarding and enrichment",
    },
    "feedback-service": {
        "url": "http://localhost:8400",
        "label": "Feedback Service",
        "description": "Alert persistence and analyst feedback",
    },
    "correlation-engine": {
        "url": "http://localhost:8600",
        "label": "Correlation Engine",
        "description": "Alert correlation and incident grouping",
    },
    "rule-generator": {
        "url": "http://localhost:8700",
        "label": "Rule Generator",
        "description": "AI-powered Sigma rule generation",
    },
    "response-orchestrator": {
        "url": "http://localhost:8800",
        "label": "Response Orchestrator",
        "description": "Autonomous adaptive defense — simulation-driven response",
    },
}

OLLAMA_URL = "http://localhost:11434"
BASE_DIR = Path(__file__).resolve().parent.parent
SIMULATION_TESTS_DIR = BASE_DIR / "outputs" / "simulation-tests"

QUICK_LINKS = [
    {"name": "Grafana", "url": "http://localhost:3000", "description": "Metrics and dashboards"},
    {"name": "Wazuh Dashboard", "url": "https://localhost:443", "description": "SIEM alerts and agents"},
    {"name": "Juice Shop", "url": "http://localhost:3002", "description": "OWASP vulnerable lab target"},
    {"name": "Prometheus", "url": "http://localhost:9090", "description": "Raw metrics"},
    {"name": "ChromaDB", "url": "http://localhost:8200", "description": "Vector database"},
    {"name": "Ollama", "url": "http://localhost:11434", "description": "LLM server"},
    {"name": "Ollama Prompt Lab", "url": "/ollama", "description": "Prompt and output viewer"},
    {"name": "Simulation Monitor", "url": "/simulation-monitor", "description": "Live simulation logs and files"},
]

# ---------------------------------------------------------------------------
# Generic proxy helper
# ---------------------------------------------------------------------------
TIMEOUT_LONG = 180  # LLM-heavy endpoints (analysis, simulation — can take 2+ min)
TIMEOUT_STD  = 15   # Fast endpoints


def _proxy(upstream_url, method="GET", timeout=TIMEOUT_STD):
    """
    Forward the current request to *upstream_url* and return a Flask response.
    Passes the original request body + Content-Type header unchanged.
    On any downstream failure returns {error: ...} with HTTP 502.
    """
    try:
        headers = {}
        if request.content_type:
            headers["Content-Type"] = request.content_type

        resp = requests.request(
            method=method,
            url=upstream_url,
            headers=headers,
            data=request.get_data(),
            params=request.args,
            timeout=timeout,
            verify=False,
        )
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        return jsonify(body), resp.status_code

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Service unavailable — connection refused", "upstream": upstream_url}), 502
    except requests.exceptions.Timeout:
        return jsonify({"error": "Service unavailable — request timed out", "upstream": upstream_url}), 504
    except Exception as exc:
        return jsonify({"error": str(exc), "upstream": upstream_url}), 502


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ollama")
def ollama_page():
    return render_template("ollama.html")


@app.route("/simulation-monitor")
def simulation_monitor_page():
    return render_template("simulation_monitor.html")


# ---------------------------------------------------------------------------
# Docker / infrastructure endpoints (exist already — kept/improved)
# ---------------------------------------------------------------------------
@app.route("/api/status")
def get_status():
    """Docker container status."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=5,
        )
        containers = []
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        c = json.loads(line)
                        containers.append({
                            "name":   c.get("Names", "unknown"),
                            "status": c.get("Status", "unknown"),
                            "ports":  c.get("Ports", ""),
                            "state":  c.get("State", "unknown"),
                        })
                    except json.JSONDecodeError:
                        continue

        healthy = sum(
            1 for c in containers
            if "healthy" in c["status"].lower() or "up" in c["status"].lower()
        )
        total = len(containers)
        overall = "healthy" if total > 0 and healthy == total else "partial" if healthy > 0 else "offline"

        return jsonify({
            "status": overall,
            "containers": containers,
            "healthy_count": healthy,
            "total_count": total,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc), "containers": [], "healthy_count": 0, "total_count": 0})


@app.route("/api/services")
def get_services():
    """Health-check all AI microservices."""
    services_status = []
    for service_id, cfg in AI_SERVICES.items():
        result = {
            "id": service_id,
            "label": cfg["label"],
            "description": cfg["description"],
            "url": cfg["url"],
            "docs_url": f"{cfg['url']}/docs",
            "status": "offline",
            "details": {},
        }
        try:
            resp = requests.get(f"{cfg['url']}/health", timeout=3, verify=False)
            if resp.status_code == 200:
                result["status"] = "healthy"
                try:
                    result["details"] = resp.json()
                except Exception:
                    result["details"] = {"message": "OK"}
            else:
                result["status"] = "degraded"
                result["details"] = {"http_status": resp.status_code}
        except requests.exceptions.ConnectionError:
            result["status"] = "offline"
            result["details"] = {"error": "Connection refused"}
        except requests.exceptions.Timeout:
            result["status"] = "timeout"
            result["details"] = {"error": "Request timed out"}
        except Exception as exc:
            result["status"] = "error"
            result["details"] = {"error": str(exc)}
        services_status.append(result)

    healthy = sum(1 for s in services_status if s["status"] == "healthy")
    return jsonify({
        "services": services_status,
        "healthy_count": healthy,
        "total_count": len(services_status),
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/ml/stats")
def get_ml_stats():
    """ML model info."""
    try:
        resp = requests.get("http://localhost:8500/models", timeout=5)
        if resp.status_code == 200:
            return jsonify(resp.json())
    except Exception:
        pass
    return jsonify({
        "models": [], "status": "offline",
        "message": "ML inference service is not running",
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/ollama/models")
def ollama_models():
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = []
        for model in data.get("models", []):
            models.append({
                "name": model.get("name"),
                "modified_at": model.get("modified_at"),
                "size": model.get("size"),
                "digest": model.get("digest"),
            })
        return jsonify({
            "status": "healthy",
            "models": models,
            "timestamp": datetime.now().isoformat(),
        })
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "offline", "error": "Ollama is not reachable", "models": []}), 502
    except requests.exceptions.Timeout:
        return jsonify({"status": "timeout", "error": "Ollama request timed out", "models": []}), 504
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc), "models": []}), 502


@app.route("/api/ollama/generate", methods=["POST"])
def ollama_generate():
    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt", "")).strip()
    model = str(payload.get("model", "")).strip() or "llama3.2:3b"
    system_prompt = str(payload.get("system", "")).strip()

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    upstream_payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": float(payload.get("temperature", 0.2)),
            "num_predict": int(payload.get("num_predict", 512)),
        },
    }
    if system_prompt:
        upstream_payload["system"] = system_prompt

    started_at = datetime.now()
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=upstream_payload,
            timeout=TIMEOUT_LONG,
        )
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        body = {
            "ok": resp.ok,
            "status_code": resp.status_code,
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "response": data.get("response", ""),
            "raw": data,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now().isoformat(),
        }
        return jsonify(body), resp.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Ollama is not reachable", "model": model, "prompt": prompt}), 502
    except requests.exceptions.Timeout:
        return jsonify({"error": "Ollama request timed out", "model": model, "prompt": prompt}), 504
    except Exception as exc:
        return jsonify({"error": str(exc), "model": model, "prompt": prompt}), 500


@app.route("/api/test-alert", methods=["POST"])
def test_alert():
    """Send a canned SSH brute-force alert through the triage pipeline."""
    payload = {
        "alert_id": f"test-{int(datetime.now().timestamp())}",
        "timestamp": datetime.now().isoformat(),
        "source_ip": "192.168.1.200",
        "destination_ip": "10.0.0.1",
        "rule_id": "5710",
        "rule_level": 10,
        "rule_description": "Multiple failed SSH login attempts (Dashboard Test)",
        "full_log": "Oct 01 12:00:00 server sshd[1234]: Failed password for invalid user admin from 192.168.1.200 port 54321 ssh2",
        "agent_name": "test-agent",
        "mitre_tactic": "Credential Access",
        "mitre_technique": "T1110.001",
    }
    try:
        resp = requests.post("http://localhost:8100/analyze", json=payload, timeout=TIMEOUT_LONG)
        result = resp.json()
        result["test_mode"] = True
        result["input_alert"] = payload
        return jsonify(result), resp.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "Alert triage service not running",
            "test_mode": True,
            "input_alert": payload,
            "demo_result": {
                "severity": "HIGH",
                "confidence": 0.91,
                "mitre_tactic": "Credential Access",
                "mitre_technique": "T1110.001 - Password Guessing",
                "summary": "SSH brute force attack detected from 192.168.1.200.",
                "recommended_actions": [
                    "Block source IP 192.168.1.200 at firewall",
                    "Review /var/log/auth.log for successful logins",
                    "Enable fail2ban if not already active",
                ],
            },
        }), 503
    except Exception as exc:
        return jsonify({"error": str(exc), "test_mode": True}), 500


@app.route("/api/logs/<container>")
def get_logs(container):
    try:
        try:
            tail = int(request.args.get("tail", 100))
        except (TypeError, ValueError):
            tail = 100
        tail = max(20, min(tail, 500))
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), container],
            capture_output=True, text=True, timeout=5,
        )
        return jsonify({"container": container, "logs": result.stdout + result.stderr, "timestamp": datetime.now().isoformat()})
    except Exception as exc:
        return jsonify({"container": container, "error": str(exc), "logs": ""})


def _json_file_summary(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if isinstance(data, list):
        return {
            "items": len(data),
            "last": data[-1] if data else None,
        }

    if not isinstance(data, dict):
        return {"value": data}

    summary = {}
    for key in (
        "status",
        "service",
        "db_connected",
        "simulation_id",
        "swarm_id",
        "duration_ms",
        "final_swarm_status",
        "single_duration_seconds",
        "single_timesteps",
        "swarm_size",
        "monte_carlo_runs",
        "swarm_timesteps",
        "timestamp",
    ):
        if key in data:
            summary[key] = data[key]

    if "results_summary" in data:
        summary["results_summary"] = data["results_summary"]
    if "config" in data:
        summary["config"] = data["config"]
    if "files" in data:
        summary["files"] = data["files"]
    return summary


def _simulation_stage(file_names):
    if "summary.json" in file_names:
        return {"key": "complete", "label": "All tests complete", "step": 6, "total": 6}
    if "04-swarm-result.json" in file_names:
        return {"key": "summary_pending", "label": "Writing summary", "step": 5, "total": 6}
    if "02-swarm-start.json" in file_names:
        return {"key": "swarm_running", "label": "Swarm simulation running", "step": 4, "total": 6}
    if "01-single-simulation.json" in file_names:
        return {"key": "single_complete", "label": "Single simulation complete, starting swarm", "step": 3, "total": 6}
    if "00-health.json" in file_names:
        return {"key": "single_running", "label": "Single simulation running", "step": 2, "total": 6}
    return {"key": "starting", "label": "Waiting for health check", "step": 1, "total": 6}


@app.route("/api/simulation-tests/latest")
def simulation_tests_latest():
    if not SIMULATION_TESTS_DIR.exists():
        return jsonify({
            "status": "empty",
            "root": str(SIMULATION_TESTS_DIR),
            "runs": [],
            "latest": None,
            "timestamp": datetime.now().isoformat(),
        })

    runs = sorted(
        [p for p in SIMULATION_TESTS_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not runs:
        return jsonify({
            "status": "empty",
            "root": str(SIMULATION_TESTS_DIR),
            "runs": [],
            "latest": None,
            "timestamp": datetime.now().isoformat(),
        })

    latest = runs[0]
    files = []
    summaries = {}
    for path in sorted(latest.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue
        stat = path.stat()
        files.append({
            "name": path.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
        if path.suffix.lower() == ".json":
            summaries[path.name] = _json_file_summary(path)

    file_names = {item["name"] for item in files}
    return jsonify({
        "status": "ok",
        "root": str(SIMULATION_TESTS_DIR),
        "runs": [
            {
                "name": p.name,
                "path": str(p),
                "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            }
            for p in runs[:10]
        ],
        "latest": {
            "name": latest.name,
            "path": str(latest),
            "modified": datetime.fromtimestamp(latest.stat().st_mtime).isoformat(),
            "stage": _simulation_stage(file_names),
            "files": files,
            "summaries": summaries,
        },
        "timestamp": datetime.now().isoformat(),
    })


# ---------------------------------------------------------------------------
# Alert Triage  (port 8100)
# ---------------------------------------------------------------------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    return _proxy("http://localhost:8100/analyze", method="POST", timeout=TIMEOUT_LONG)


@app.route("/api/analyze/async", methods=["POST"])
def analyze_async():
    return _proxy("http://localhost:8100/analyze/async", method="POST", timeout=TIMEOUT_LONG)


@app.route("/api/jobs/<job_id>")
def get_job(job_id):
    return _proxy(f"http://localhost:8100/jobs/{job_id}", timeout=TIMEOUT_STD)


@app.route("/api/workers/stats")
def workers_stats():
    return _proxy("http://localhost:8100/workers/stats", timeout=TIMEOUT_STD)


# ---------------------------------------------------------------------------
# Feedback Service  (port 8400)
# ---------------------------------------------------------------------------
@app.route("/api/alerts")
def get_alerts():
    return _proxy("http://localhost:8400/alerts", timeout=TIMEOUT_STD)


@app.route("/api/alerts/<alert_id>")
def get_alert(alert_id):
    return _proxy(f"http://localhost:8400/alerts/{alert_id}", timeout=TIMEOUT_STD)


@app.route("/api/feedback/<alert_id>", methods=["POST"])
def post_feedback(alert_id):
    return _proxy(f"http://localhost:8400/feedback/{alert_id}", method="POST", timeout=TIMEOUT_STD)


@app.route("/api/feedback/stats")
def feedback_stats():
    return _proxy("http://localhost:8400/feedback/stats", timeout=TIMEOUT_STD)


# ---------------------------------------------------------------------------
# Correlation Engine / Simulation / Risk  (port 8600)
# ---------------------------------------------------------------------------
@app.route("/api/incidents")
def get_incidents():
    return _proxy("http://localhost:8600/incidents", timeout=TIMEOUT_STD)


@app.route("/api/incidents/active")
def get_active_incidents():
    return _proxy("http://localhost:8600/incidents/active", timeout=TIMEOUT_STD)


@app.route("/api/incidents/<incident_id>")
def get_incident(incident_id):
    return _proxy(f"http://localhost:8600/incidents/{incident_id}", timeout=TIMEOUT_STD)


@app.route("/api/predict/<stage>")
def predict_stage(stage):
    return _proxy(f"http://localhost:8600/predict/{stage}", timeout=TIMEOUT_STD)


@app.route("/api/simulate", methods=["POST"])
def simulate():
    return _proxy("http://localhost:8600/simulate", method="POST", timeout=TIMEOUT_LONG)


@app.route("/api/simulate/environment/from-wazuh", methods=["POST"])
def simulate_env_from_wazuh():
    return _proxy("http://localhost:8600/simulate/environment/from-wazuh", method="POST", timeout=TIMEOUT_LONG)


@app.route("/api/simulate/swarm/start", methods=["POST"])
def simulate_swarm_start():
    return _proxy("http://localhost:8600/simulate/swarm/start", method="POST", timeout=30)


@app.route("/api/simulate/swarm/<swarm_id>/status")
def simulate_swarm_status(swarm_id):
    return _proxy(f"http://localhost:8600/simulate/swarm/{swarm_id}/status", timeout=TIMEOUT_STD)


@app.route("/api/simulate/swarm/<swarm_id>/result")
def simulate_swarm_result(swarm_id):
    return _proxy(f"http://localhost:8600/simulate/swarm/{swarm_id}/result", timeout=TIMEOUT_STD)


@app.route("/api/simulate/swarm/trend")
def simulate_swarm_trend():
    return _proxy("http://localhost:8600/simulate/swarm/trend", timeout=TIMEOUT_STD)


@app.route("/api/simulate/research/metrics")
def simulate_research_metrics():
    return _proxy("http://localhost:8600/simulate/research/metrics", timeout=TIMEOUT_STD)


@app.route("/api/simulate/research/export", methods=["POST"])
def simulate_research_export():
    return _proxy("http://localhost:8600/simulate/research/export", method="POST", timeout=TIMEOUT_STD)


@app.route("/api/simulate/<simulation_id>/chat", methods=["POST"])
def simulate_chat(simulation_id):
    return _proxy(f"http://localhost:8600/simulate/{simulation_id}/chat", method="POST", timeout=TIMEOUT_LONG)


@app.route("/api/environment/default")
def get_default_environment():
    import os
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'simulation', 'default-environment.json')
    try:
        with open(env_path) as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": f"Default environment not found at {env_path}"}), 404


@app.route("/api/risk-scores")
def risk_scores():
    return _proxy("http://localhost:8600/risk-scores", timeout=TIMEOUT_STD)


@app.route("/api/risk-summary")
def risk_summary():
    return _proxy("http://localhost:8600/risk-summary", timeout=TIMEOUT_STD)


@app.route("/api/risk-scores/refresh", methods=["POST"])
def risk_scores_refresh():
    return _proxy("http://localhost:8600/risk-scores/refresh", method="POST", timeout=TIMEOUT_LONG)


# ---------------------------------------------------------------------------
# Rule Generator  (port 8700)
# ---------------------------------------------------------------------------
@app.route("/api/generate-rule", methods=["POST"])
def generate_rule():
    return _proxy("http://localhost:8700/generate", method="POST", timeout=TIMEOUT_LONG)


@app.route("/api/rules")
def get_rules():
    return _proxy("http://localhost:8700/rules", timeout=TIMEOUT_STD)


@app.route("/api/rules/pending")
def get_pending_rules():
    return _proxy("http://localhost:8700/rules/pending", timeout=TIMEOUT_STD)


@app.route("/api/rules/<rule_id>/approve", methods=["PUT"])
def approve_rule(rule_id):
    return _proxy(f"http://localhost:8700/rules/{rule_id}/approve", method="PUT", timeout=TIMEOUT_STD)


# ---------------------------------------------------------------------------
# Response Orchestrator  (port 8800)
# ---------------------------------------------------------------------------
@app.route("/api/defend", methods=["POST"])
def trigger_defense():
    return _proxy("http://localhost:8800/defend", method="POST", timeout=TIMEOUT_LONG)


@app.route("/api/defense/plans")
def defense_plans():
    return _proxy("http://localhost:8800/plans", timeout=TIMEOUT_STD)


@app.route("/api/defense/plans/<plan_id>")
def defense_plan_detail(plan_id):
    return _proxy(f"http://localhost:8800/plans/{plan_id}", timeout=TIMEOUT_STD)


@app.route("/api/defense/approvals")
def defense_approvals():
    return _proxy("http://localhost:8800/approvals", timeout=TIMEOUT_STD)


@app.route("/api/defense/plans/<plan_id>/actions/<action_id>/approve", methods=["POST"])
def defense_approve_action(plan_id, action_id):
    return _proxy(
        f"http://localhost:8800/plans/{plan_id}/actions/{action_id}/approve",
        method="POST", timeout=TIMEOUT_STD,
    )


@app.route("/api/d3fend/lookup/<technique_id>")
def d3fend_lookup(technique_id):
    return _proxy(f"http://localhost:8800/d3fend/lookup/{technique_id}", timeout=TIMEOUT_STD)


@app.route("/api/d3fend/techniques")
def d3fend_techniques():
    return _proxy("http://localhost:8800/d3fend/techniques", timeout=TIMEOUT_STD)


# ---------------------------------------------------------------------------
# Wazuh Integration  (port 8002)
# ---------------------------------------------------------------------------
@app.route("/api/webhook", methods=["POST"])
def webhook():
    return _proxy("http://localhost:8002/webhook", method="POST", timeout=TIMEOUT_STD)


# ---------------------------------------------------------------------------
# RAG Service  (port 8300)
# ---------------------------------------------------------------------------
@app.route("/api/rag/retrieve", methods=["POST"])
def rag_retrieve():
    return _proxy("http://localhost:8300/retrieve", method="POST", timeout=TIMEOUT_LONG)


@app.route("/api/rag/collections")
def rag_collections():
    return _proxy("http://localhost:8300/collections", timeout=TIMEOUT_STD)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Aegis Guard Command Center starting…")
    print("Access at: http://localhost:5050")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
