from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DISPLAY_FILES = [
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / "mkdocs.yml",
    ROOT / "pytest.ini",
    ROOT / "requirements-security.txt",
    ROOT / "AI-SOC-Launcher.py",
    ROOT / "deploy-ai-soc.ps1",
    ROOT / "deploy-ai-soc.sh",
    ROOT / "deploy.ps1",
    ROOT / "quickstart.sh",
    ROOT / "START-AI-SOC.bat",
    ROOT / "RUN-SIMULATION-TESTS.bat",
    ROOT / "WATCH-OLLAMA-LOGS.bat",
    ROOT / "WRITE-TEST-WAZUH-AI-EVENT.bat",
    ROOT / "start-ai-soc-full.ps1",
    ROOT / "dashboard" / "app.py",
    ROOT / "dashboard" / "templates" / "index.html",
    ROOT / "config" / "grafana" / "dashboards" / "ai_soc_overview.json",
    ROOT / "config" / "grafana" / "provisioning" / "dashboards" / "dashboards.yml",
    ROOT / "config" / "alertmanager" / "alertmanager.yml",
    ROOT / "config" / "prometheus" / "prometheus.yml",
    ROOT / "config" / "prometheus" / "alerts" / "ai-soc-alerts.yml",
    ROOT / "config" / "filebeat" / "filebeat.yml",
    ROOT / "config" / "suricata" / "suricata.yaml",
    ROOT / "config" / "zeek" / "local.zeek",
    ROOT / "config" / "wazuh-dashboard" / "opensearch_dashboards.yml",
    ROOT / "config" / "simulation" / "default-environment.json",
    ROOT / "ml_training" / "README.md",
    ROOT / "services" / "README.md",
    ROOT / "services" / "feedback-service" / "main.py",
    ROOT / "services" / "response-orchestrator" / "main.py",
    ROOT / "services" / "response-orchestrator" / "d3fend.py",
    ROOT / "services" / "wazuh-integration" / "Dockerfile",
    ROOT / "services" / "wazuh-integration" / "README.md",
    ROOT / "services" / "wazuh-integration" / "main.py",
    ROOT / "services" / "wazuh-integration" / "indexer_writer.py",
    ROOT / "services" / "retraining" / "retrain.py",
    ROOT / "scripts" / "run-simulation-tests.ps1",
    ROOT / "scripts" / "watch-ollama-logs.ps1",
    ROOT / "scripts" / "setup-configs.sh",
    ROOT / "scripts" / "generate_secure_credentials.py",
    ROOT / "scripts" / "generate_30_figures.py",
    ROOT / "scripts" / "generate_30_mermaid.py",
    ROOT / "scripts" / "generate_thesis_svg_diagrams.py",
    ROOT / "tests" / "README.md",
    ROOT / "tests" / "requirements.txt",
    ROOT / "tests" / "conftest.py",
    ROOT / "tests" / "validate_tests.py",
    ROOT / "tests" / "browser" / "test_dashboards.py",
    ROOT / "tests" / "load" / "locustfile.py",
    ROOT / "tests" / "e2e" / "test_complete_workflows.py",
]


for compose_path in (ROOT / "docker-compose").glob("*"):
    if compose_path.is_file() and compose_path.suffix.lower() in {".md", ".yml", ".yaml"}:
        DISPLAY_FILES.append(compose_path)


for docs_path in (ROOT / "docs").rglob("*"):
    if docs_path.is_file() and docs_path.suffix.lower() in {".md", ".html", ".yml", ".yaml", ".css", ".js"}:
        DISPLAY_FILES.append(docs_path)


REPLACEMENTS = [
    ("AI-SOC Command Center", "Aegis Guard Command Center"),
    ("AI-SOC Control Center", "Aegis Guard Control Center"),
    ("AI-SOC Documentation", "Aegis Guard Documentation"),
    ("AI-SOC Dashboards", "Aegis Guard Dashboards"),
    ("AI-SOC Dashboard", "Aegis Guard Dashboard"),
    ("AI-SOC Overview", "Aegis Guard Overview"),
    ("AI-SOC Platform", "Aegis Guard"),
    ("AI-SOC Platform", "Aegis Guard Platform"),
    ("AI-SOC platform", "Aegis Guard platform"),
    ("AI-SOC services", "Aegis Guard services"),
    ("AI-SOC service", "Aegis Guard service"),
    ("AI-SOC stack", "Aegis Guard stack"),
    ("AI-SOC infrastructure", "Aegis Guard infrastructure"),
    ("AI-SOC deployment", "Aegis Guard deployment"),
    ("AI-SOC Deployment", "Aegis Guard Deployment"),
    ("AI-SOC QUICKSTART", "Aegis Guard QUICKSTART"),
    ("AI-SOC Quickstart", "Aegis Guard Quickstart"),
    ("AI-SOC One-Click Startup", "Aegis Guard One-Click Startup"),
    ("AI-SOC Simulation Tests", "Aegis Guard Simulation Tests"),
    ("AI-SOC Ollama", "Aegis Guard Ollama"),
    ("AI-SOC SSL Certificate Generation", "Aegis Guard SSL Certificate Generation"),
    ("AI-SOC Certificate Generator", "Aegis Guard Certificate Generator"),
    ("AI-SOC PRODUCTION CREDENTIALS", "Aegis Guard PRODUCTION CREDENTIALS"),
    ("AI-SOC Production", "Aegis Guard Production"),
    ("AI-SOC Testing", "Aegis Guard Testing"),
    ("AI-SOC Testing Framework", "Aegis Guard Testing Framework"),
    ("AI-SOC RAG Team", "Aegis Guard RAG Team"),
    ("AI-SOC ML Team", "Aegis Guard ML Team"),
    ("AI-SOC LLM Team", "Aegis Guard LLM Team"),
    ("AI-SOC Platform Team", "Aegis Guard Team"),
    ("AI-SOC Performance Engineering Team", "Aegis Guard Performance Engineering Team"),
    ("AI-SOC Project Contributors", "Aegis Guard Project Contributors"),
    ("AI-SOC Project", "Aegis Guard Project"),
    ("AI-SOC Webhook", "Aegis Guard Webhook"),
    ("AI-SOC Wazuh Event Test", "Aegis Guard Wazuh Event Test"),
    ("AI-SOC Continuous Retraining Pipeline", "Aegis Guard Continuous Retraining Pipeline"),
    ("AI-SOC Response Orchestrator", "Aegis Guard Response Orchestrator"),
    ("AI-SOC Default Environment", "Aegis Guard Default Environment"),
    ("AI-SOC Thesis", "Aegis Guard Thesis"),
    ("AI-SOC System Architecture", "Aegis Guard System Architecture"),
    ("AI-SOC decisions", "Aegis Guard decisions"),
    ("AI-SOC workflow", "Aegis Guard workflow"),
    ("AI-SOC metrics", "Aegis Guard metrics"),
    ("AI-SOC logs", "Aegis Guard logs"),
    ("START AI-SOC", "START Aegis Guard"),
    ("STOP AI-SOC", "STOP Aegis Guard"),
    ("AI-SOC Running", "Aegis Guard Running"),
    ("AI-SOC is ready", "Aegis Guard is ready"),
    ("AI-SOC stopped", "Aegis Guard stopped"),
    ("AI-SOC Launcher", "Aegis Guard Launcher"),
    ("AI-SOC Graphical Launcher", "Aegis Guard Graphical Launcher"),
    ("AI-Augmented Security Operations Center", "AI-Driven Security Operations Center"),
    ("AI-assisted security operations center", "AI-driven security operations center"),
    ("AI-augmented security operations", "AI-driven security operations"),
    ("AI-augmented SOC", "AI-driven SOC"),
    ("AI-augmented", "AI-driven"),
    ("AI-SOC", "Aegis Guard"),
]


PROTECTED_SUBSTRINGS = [
    "AI_SOC",
    "START-AI-SOC.bat",
    "AI-SOC-Launcher.py",
    "ai-soc-events",
    "ai-soc-alerts",
    "ai_soc_overview",
]


def protect(text: str) -> tuple[str, dict[str, str]]:
    tokens: dict[str, str] = {}
    for i, value in enumerate(PROTECTED_SUBSTRINGS):
        token = f"__AEGIS_PROTECTED_{i}__"
        if value in text:
            text = text.replace(value, token)
            tokens[token] = value
    return text, tokens


def unprotect(text: str, tokens: dict[str, str]) -> str:
    for token, value in tokens.items():
        text = text.replace(token, value)
    return text


def main() -> None:
    changed: list[Path] = []
    seen = set()
    for path in DISPLAY_FILES:
        if path in seen or not path.exists() or not path.is_file():
            continue
        seen.add(path)
        original = path.read_text(encoding="utf-8", errors="ignore")
        text, tokens = protect(original)
        for old, new in REPLACEMENTS:
            text = text.replace(old, new)
        text = unprotect(text, tokens)
        if text != original:
            path.write_text(text, encoding="utf-8", newline="")
            changed.append(path.relative_to(ROOT))
    print(f"Changed {len(changed)} files")
    for path in changed:
        print(path)


if __name__ == "__main__":
    main()
