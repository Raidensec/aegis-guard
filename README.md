# AI-Driven Security Operations Center

Local AI services, machine-learning intrusion detection, alert enrichment, attack-campaign simulation, and response planning for security operations.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docker Compose](https://img.shields.io/badge/docker-compose-blue.svg)](https://docs.docker.com/compose/)
[![Dataset: CICIDS2017](https://img.shields.io/badge/dataset-CICIDS2017-green.svg)](datasets/CICIDS2017/README.md)

Aegis Guard is an AI-driven security operations center platform. It combines trained IDS models, local LLM alert triage, retrieval over security knowledge, Wazuh integration, incident correlation, swarm-scale attack simulation, and a prototype response orchestrator.

The project is intentionally local-first: security event data is processed through local services and Ollama-backed LLM inference rather than a hosted LLM API.

## What This Is

Aegis Guard answers one operational question:

> Given a noisy stream of alerts and a modeled environment, which threats matter, how might an attacker proceed, and what defensive action should be considered first?

It does that through several cooperating services:

- ML inference over CICIDS2017-style network-flow features
- LLM alert triage with structured JSON output and confidence reporting
- RAG retrieval over MITRE ATT&CK, CVE data, and security runbooks
- Wazuh alert ingestion and enrichment
- Feedback capture for analyst labels and retraining workflows
- Incident correlation with kill-chain tracking
- Attack-campaign simulation with attacker and defender archetypes
- Response planning with D3FEND mapping and graduated autonomy controls

This is not a drop-in production SOC. It is a local platform with runnable services, trained artifacts, and some deliberately stubbed production integrations.

## Current Status

| Area | Status | Notes |
|---|---|---|
| ML inference API | Implemented | FastAPI service using trained Random Forest, XGBoost, and Decision Tree artifacts in `models/`; expects 77 features. |
| Alert triage service | Implemented | FastAPI + Ollama client, ML-aware prompt enrichment, async worker pool, feedback persistence. |
| RAG service | Implemented | ChromaDB-backed retrieval with MITRE, CVE, and runbook ingestion endpoints. |
| Wazuh integration | Implemented | Webhook receiver and alert router for triage/RAG enrichment. |
| Feedback service | Implemented | PostgreSQL-backed alert and analyst-feedback storage. |
| Correlation engine | Implemented | Incident grouping, kill-chain progression, Markov prediction, risk scoring, simulator APIs. |
| Swarm simulation | Prototype | Monte Carlo leader/follower simulation with attacker and defender archetypes. |
| Response orchestrator | Prototype implemented | D3FEND mapping, plan generation, approval tiers, execution workflow, verification loop. |
| Firewall, EDR, identity adapters | Stubbed | Interfaces exist; production vendor adapters still need real API implementations. |
| Full deployment script | Implemented | `deploy-ai-soc.sh` and `deploy-ai-soc.ps1` orchestrate SIEM, AI services, and monitoring. |
| Vulnerable lab target | Implemented | OWASP Juice Shop runs in Docker on the AI services network for local attack/defense testing. |
| `docker-compose/integrated-stack.yml` | Experimental/stale | References gateway/webhook services that are not present in this checkout; use the compose files listed below. |

## Architecture

```mermaid
flowchart TB
    events["Security Events and Network Flow Data"]

    subgraph collect["Detection and Collection"]
        wazuh["Wazuh SIEM"]
        suricata["Suricata IDS"]
        zeek["Zeek"]
        filebeat["Filebeat"]
    end

    integration["Wazuh Integration :8002<br/>Webhook receiver, alert routing, enrichment"]

    subgraph analysis["AI Analysis Layer"]
        triage["Alert Triage :8100<br/>Local LLM analysis<br/>ML-aware confidence<br/>Async worker pool"]
        rag["RAG Service :8300<br/>MITRE, CVE, runbooks<br/>ChromaDB vector store"]
        ml["ML Inference :8500<br/>Random Forest, XGBoost, Decision Tree<br/>77 CICIDS2017 features"]
    end

    subgraph memory["Learning and Knowledge"]
        feedback["Feedback Service :8400<br/>Alert history<br/>Analyst labels<br/>Retraining input"]
        retraining["Retraining Pipeline<br/>Champion/challenger promotion<br/>Model reload workflow"]
        rules["Rule Generator :8700<br/>Sigma draft generation<br/>Historical back-testing"]
    end

    subgraph incidents["Incident Intelligence"]
        correlation["Correlation Engine :8600<br/>Incident grouping<br/>Kill-chain state<br/>Risk scoring and simulation"]
        swarm["Attack-Campaign Simulator<br/>Attacker and defender archetypes<br/>Monte Carlo swarm runs"]
    end

    orchestrator["Response Orchestrator :8800<br/>D3FEND countermeasures<br/>Approval tiers<br/>Adapter execution<br/>Verification by re-simulation and monitoring"]

    subgraph observe["Observability"]
        prometheus["Prometheus"]
        grafana["Grafana"]
        alertmanager["Alertmanager"]
        loki["Loki"]
    end

    events --> collect
    collect --> integration
    integration --> triage
    integration --> rag
    triage <--> rag
    triage --> ml
    triage --> feedback
    ml --> triage
    feedback --> retraining
    retraining --> ml
    triage --> correlation
    integration --> correlation
    correlation --> swarm
    swarm --> correlation
    correlation --> orchestrator
    orchestrator --> rules
    orchestrator --> feedback
    orchestrator --> swarm

    triage -. metrics .-> prometheus
    rag -. metrics .-> prometheus
    ml -. metrics .-> prometheus
    correlation -. metrics .-> prometheus
    orchestrator -. metrics .-> prometheus
    prometheus --> grafana
    prometheus --> alertmanager
    integration -. logs .-> loki
```

## Repository Layout

```text
.
|-- docker-compose/              Compose stacks for SIEM, AI services, monitoring
|-- services/
|   |-- alert-triage/            LLM alert analysis service
|   |-- rag-service/             Security knowledge retrieval service
|   |-- feedback-service/        Alert and analyst feedback persistence
|   |-- wazuh-integration/       Wazuh webhook/API integration
|   |-- correlation-engine/      Incident grouping, prediction, simulation
|   |-- response-orchestrator/   Defense planning and approval workflow
|   |-- rule-generator/          Sigma rule generation prototype
|   |-- retraining/              Feedback-driven model retraining
|   `-- common/                  Shared security, logging, pipeline utilities
|-- ml_training/                 CICIDS2017 training and inference API
|-- models/                      Trained model and preprocessing artifacts
|-- config/                      Wazuh, Grafana, Prometheus, simulation configs
|-- docs/                        MkDocs documentation site content
|-- datasets/                    Dataset notes, validation, checksums
`-- tests/                       Unit, integration, security, browser, load scaffolding
```

## Quick Start

### Requirements

- Docker Engine 23+ and Docker Compose v2
- Python 3.10+ for local development
- 16 GB RAM minimum; 32 GB recommended for the full stack
- 20 GB+ free disk for images, models, and service data
- Linux for the most complete SIEM/network-sensor setup
- Windows/macOS supported for local AI-service development and the Windows-compatible SIEM compose path

### One-command deployment

Before deployment, copy `.env.example` to `.env` and replace every `CHANGE_ME` value with a unique local secret. The deployment scripts copy the template if `.env` is missing, but do not generate secret values.

Linux/macOS:

```bash
git clone https://github.com/Raidensec/aegis-guard.git
cd aegis-guard
./deploy-ai-soc.sh
```

Windows PowerShell:

```powershell
git clone https://github.com/Raidensec/aegis-guard.git
cd aegis-guard
.\deploy-ai-soc.ps1
```

The deployment script performs three phases:

1. Starts the Wazuh SIEM core
2. Builds and starts AI services and the Juice Shop lab target from `docker-compose/ai-services.yml`
3. Starts the monitoring stack from `docker-compose/monitoring-stack.yml`

It also creates `.env` from `.env.example` when needed, generates local certificates when possible, pulls the configured Ollama model, and triggers RAG knowledge-base ingestion.

### Manual compose deployment

```bash
# SIEM core
docker compose -f docker-compose/phase1-siem-core.yml up -d

# AI services
docker compose -f docker-compose/ai-services.yml up -d --build

# Optional: start only the vulnerable lab target
docker compose -f docker-compose/ai-services.yml up -d juice-shop

# Monitoring
docker compose -f docker-compose/monitoring-stack.yml up -d
```

On Windows or macOS, use:

```bash
docker compose -f docker-compose/phase1-siem-core-windows.yml up -d
```

### Stop the stack

```bash
./deploy-ai-soc.sh --stop
```

or:

```powershell
.\deploy-ai-soc.ps1 -Stop
```

## Service URLs

| Service | URL |
|---|---|
| Wazuh Dashboard | `https://localhost:443` |
| Wazuh Indexer API | `https://localhost:9200` |
| Wazuh API | `https://localhost:55000` |
| Wazuh Integration | `http://localhost:8002/docs` |
| Alert Triage | `http://localhost:8100/docs` |
| RAG Service | `http://localhost:8300/docs` |
| Feedback Service | `http://localhost:8400/docs` |
| ML Inference | `http://localhost:8500/docs` |
| Correlation Engine | `http://localhost:8600/docs` |
| Rule Generator | `http://localhost:8700/docs` |
| Response Orchestrator | `http://localhost:8800/docs` |
| OWASP Juice Shop Lab Target | `http://localhost:3002` |
| Ollama | `http://localhost:11434` |
| ChromaDB | `http://localhost:8200` |
| Grafana | `http://localhost:3000` |
| Prometheus | `http://localhost:9090` |
| Alertmanager | `http://localhost:9093` |

Replace all `CHANGE_ME` values in `.env` before starting services. Use this project only in an isolated lab unless you complete the hardening steps below.

## Lab Target: OWASP Juice Shop

The AI services compose file includes OWASP Juice Shop as an intentionally vulnerable local web target.

```bash
docker compose -f docker-compose/ai-services.yml up -d juice-shop
```

Open `http://localhost:3002` from the host. Other containers on the AI services network can reach it at `http://juice-shop:3000`. The host port can be changed with `JUICE_SHOP_HOST_PORT` in `.env`.

When the full AI services stack is running, Juice Shop's LLM-backed chatbot challenges are configured to use Aegis Guard's Ollama service at `http://ollama:11434/v1` with `JUICE_SHOP_LLM_MODEL`.

### Juice Shop to Wazuh pipeline

Juice Shop access logs are persisted in the shared Docker volume `ai-soc-juice-shop-logs`. The Wazuh manager mounts that volume read-only at `/var/log/juice-shop` and monitors `access.log.*` through `config/wazuh-manager/ossec.conf`.

Custom Wazuh rules in `config/wazuh-manager/rules/local_rules.xml` emit:

- Rule `100500`: every Juice Shop HTTP access event.
- Rule `100501`: Juice Shop HTTP 4xx/5xx events.
- Rule `100502`: failed Juice Shop login attempts on `POST /rest/user/login` with status `401`.
- Rule `100503`: SQL injection probes against Juice Shop URLs.
- Rule `100504`: XSS probes against Juice Shop URLs.
- Rule `100505`: path traversal probes against Juice Shop URLs.

After changing the pipeline, recreate the affected containers so the shared volume and Wazuh rules are mounted:

```bash
docker compose -f docker-compose/ai-services.yml up -d --force-recreate juice-shop
docker compose -f docker-compose/phase1-siem-core-windows.yml up -d --force-recreate wazuh-manager
```

## Usage Examples

### Analyze a security alert

```bash
curl -X POST http://localhost:8100/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "test-001",
    "rule_description": "SSH brute force attack detected",
    "rule_level": 10,
    "source_ip": "203.0.113.42",
    "dest_ip": "10.0.1.50",
    "dest_port": 22,
    "raw_log": "Failed password for root from 203.0.113.42 port 45678 ssh2"
  }'
```

Expected response shape:

```json
{
  "alert_id": "test-001",
  "severity": "high",
  "category": "intrusion_attempt",
  "confidence": 0.92,
  "summary": "SSH brute force activity from 203.0.113.42 against root login",
  "is_true_positive": true,
  "iocs": [
    {
      "ioc_type": "ip",
      "value": "203.0.113.42",
      "confidence": 0.95
    }
  ],
  "mitre_techniques": ["T1110.001"],
  "recommendations": [
    {
      "action": "Block source IP at the perimeter firewall",
      "priority": 1,
      "rationale": "Prevents continued brute-force attempts from the same source"
    }
  ]
}
```

### Run ML inference directly

The inference API expects exactly 77 flow features in the trained feature order stored in `models/feature_names.pkl`.

```bash
python - <<'PY'
import json
import urllib.request

payload = json.dumps({
    "features": [0.0] * 77,
    "model_name": "random_forest",
}).encode()

request = urllib.request.Request(
    "http://localhost:8500/predict",
    data=payload,
    headers={"Content-Type": "application/json"},
)

print(urllib.request.urlopen(request, timeout=10).read().decode())
PY
```

The all-zero vector is only a smoke-test payload. Real predictions should use the trained feature order in `models/feature_names.pkl`.

### Retrieve knowledge-base context

```bash
curl -X POST http://localhost:8300/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "credential dumping LSASS memory",
    "collection": "mitre_attack",
    "top_k": 3
  }'
```

### Submit analyst feedback

```bash
curl -X POST http://localhost:8400/feedback/test-001 \
  -H "Content-Type: application/json" \
  -d '{
    "analyst_id": "analyst1",
    "is_false_positive": false,
    "true_label": "ATTACK",
    "notes": "Confirmed brute-force source"
  }'
```

### Correlate alerts and inspect incidents

```bash
curl http://localhost:8600/incidents
curl http://localhost:8600/predict/reconnaissance
```

### Run attack-campaign simulation

```bash
# Single campaign
curl -X POST "http://localhost:8600/simulate?timesteps=3"

# Swarm simulation
curl -X POST "http://localhost:8600/simulate/swarm/start?swarm_size=100&monte_carlo_runs=5&timesteps=6"

# Poll status
curl "http://localhost:8600/simulate/swarm/SWARM-ID/status"

# Fetch result
curl "http://localhost:8600/simulate/swarm/SWARM-ID/result"
```

### Trigger response planning

```bash
curl -X POST http://localhost:8800/defend \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "INC-20250324-ab12",
    "auto_execute": false,
    "dry_run": true
  }'
```

Use dry-run mode while evaluating the response orchestrator. Firewall, EDR, and identity actions are adapter stubs unless replaced with production integrations.

## ML Results

The ML baseline is trained on CICIDS2017-style network-flow data with binary `BENIGN` vs `ATTACK` classification.

| Model | Accuracy | False Positive Rate | Notes |
|---|---:|---:|---|
| Random Forest | 99.28% | 0.25% | Best overall balance in current artifacts. |
| XGBoost | 99.21% | 0.09% | Lowest false-positive rate. |
| Decision Tree | 99.10% | 0.50% | Interpretable baseline. |

Artifacts:

- `models/random_forest_ids.pkl`
- `models/xgboost_ids.pkl`
- `models/decision_tree_ids.pkl`
- `models/scaler.pkl`
- `models/label_encoder.pkl`
- `models/feature_names.pkl`

Training and deployment notes:

- [ml_training/README.md](ml_training/README.md)
- [ml_training/inference_api.py](ml_training/inference_api.py)
- [docs/experiments/ml-performance.md](docs/experiments/ml-performance.md)

## Attack Campaign Simulation

The correlation engine supports configurable multi-agent campaign simulations against a modeled environment.

## Response Orchestration

The response orchestrator turns detected techniques and simulation output into candidate defensive actions:

1. Fetch incident context from the correlation engine
2. Optionally run simulation
3. Map ATT&CK techniques to D3FEND countermeasures
4. Score actions by impact, safety, and confidence
5. Assign an approval tier
6. Execute auto-safe actions or queue human-required actions
7. Verify outcome through re-simulation and monitoring
8. Record outcome for feedback

Approval tiers:

| Tier | Behavior |
|---|---|
| Observe | Log only. |
| Recommend | Analyst decides. |
| Auto-safe | Low-blast action may execute automatically. |
| Auto-veto | Medium-blast action can execute with a veto window. |
| Human-required | Analyst approval required. |

Safety invariant: actions affecting critical assets or high-blast actions require human approval regardless of model confidence.

## Testing

Install test dependencies:

```bash
pip install -r tests/requirements.txt
```

Run the full suite:

```bash
pytest tests/
```

Run the structural validator:

```bash
PYTHONIOENCODING=utf-8 python tests/validate_tests.py
```

On Windows PowerShell:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python tests\validate_tests.py
```

Current testing notes:

- Some tests and CI snippets still assume 78 ML features, while the current API and artifacts use 77.
- GitHub Actions workflow files are not included in this repository snapshot; test source files are retained.
- Browser, load, and integration tests require the relevant local services to be running.

## Security Notes

Aegis Guard is built for a lab environment unless hardened further.

Before production-like use:

- Replace every default password in `.env`
- Keep `.env`, generated certificates, and credentials out of git
- Enable TLS where services communicate across hosts
- Add API authentication to exposed service endpoints
- Review container network boundaries and host-network sensor settings
- Replace response-action stubs with audited vendor integrations
- Validate LLM output before using it for automated action
- Treat ML predictions from alert metadata as low confidence unless full 77-feature flow data is present

The repository includes additional guidance in:

- [docs/security/guide.md](docs/security/guide.md)

## Known Gaps

- Production firewall, EDR, and identity adapters are not implemented.
- Adversarial ML evasion testing has not been completed.
- The ML model is binary only; multi-class attack labeling remains future work.
- Simulator results have not been benchmarked against real red-team outcomes.
- Some service-level README files lag behind the current implementation status.
- `docker-compose/integrated-stack.yml` is not the canonical deployment path in this checkout.
- Feedback-loop protection against bad or malicious labels is not implemented.
- Longitudinal evidence for retraining improvement requires operational data over time.

## Roadmap

- Align all tests and CI around the current 77-feature model contract
- Replace stubbed response adapters with real pfSense, CrowdStrike, Microsoft Defender, or identity-provider integrations
- Add multi-class IDS classification
- Add adversarial robustness evaluation
- Add graph-based incident correlation
- Auto-populate simulation environments from Wazuh inventory and vulnerability data
- Validate simulator predictions against controlled adversary-emulation exercises
- Add stronger feedback-label validation before model retraining

## Documentation

| Topic | Link |
|---|---|
| Quickstart | [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) |
| Installation | [docs/getting-started/installation.md](docs/getting-started/installation.md) |
| Architecture overview | [docs/architecture/overview.md](docs/architecture/overview.md) |
| Deployment guide | [docs/deployment/guide.md](docs/deployment/guide.md) |
| Wazuh integration | [docs/WAZUH_INTEGRATION_GUIDE.md](docs/WAZUH_INTEGRATION_GUIDE.md) |
| ML accuracy | [docs/ai-soc/ml-accuracy.md](docs/ai-soc/ml-accuracy.md) |
| API docs | [docs/api/ml-inference.md](docs/api/ml-inference.md) |
