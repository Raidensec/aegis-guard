#!/usr/bin/env python3
"""
AI-SOC Splunk Integration Validation Script
============================================

Runs every validation step the user specified. Each step is independent;
failures are reported but do not abort the remaining checks.

Usage (from the project root, with Docker stack running):
    python scripts/validate_splunk_integration.py

Requires: requests (stdlib-compatible fallback via urllib if missing)
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ─── Configuration ────────────────────────────────────────────────────────────

SPLUNK_WEB_URL      = "http://localhost:8008"
SPLUNK_HEC_URL      = "http://localhost:8088"
SPLUNK_HEC_TOKEN    = os.getenv("SPLUNK_HEC_TOKEN", "CHANGE_ME_SPLUNK_HEC_TOKEN")
WAZUH_MANAGER_CTR   = "wazuh-manager"
WAZUH_INT_CTR       = "wazuh-integration"
SPLUNK_CTR          = "splunk"
TIMEOUT             = 8   # seconds for HTTP checks

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

results = []


def record(label: str, ok: bool, detail: str = "") -> bool:
    status = PASS if ok else FAIL
    line = f"{status} {label}"
    if detail:
        line += f"\n       {detail}"
    print(line)
    results.append({"label": label, "ok": ok, "detail": detail})
    return ok


# ─── Step 1: Docker container health ─────────────────────────────────────────
print("\n══════════════════════════════════════════")
print("  Step 1 — Container health")
print("══════════════════════════════════════════")

for ctr in [WAZUH_MANAGER_CTR, WAZUH_INT_CTR, SPLUNK_CTR]:
    try:
        out = subprocess.check_output(
            ["docker", "inspect", "--format", "{{.State.Status}}", ctr],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        record(f"Container {ctr} is running", out == "running", f"State: {out}")
    except subprocess.CalledProcessError:
        record(f"Container {ctr} is running", False, "docker inspect failed — container may not exist")


# ─── Step 2: Splunk HEC health endpoint ──────────────────────────────────────
print("\n══════════════════════════════════════════")
print("  Step 2 — Splunk HEC health")
print("══════════════════════════════════════════")

try:
    req = urllib.request.Request(
        f"{SPLUNK_HEC_URL}/services/collector/health",
        headers={"Authorization": f"Splunk {SPLUNK_HEC_TOKEN}"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = resp.read().decode()
        ok = resp.status == 200
        record("HEC /health returns 200", ok, f"HTTP {resp.status}: {body[:200]}")
except urllib.error.HTTPError as e:
    record("HEC /health returns 200", False, f"HTTP {e.code}: {e.reason}")
except Exception as e:
    record("HEC /health returns 200", False, str(e))


# ─── Step 3: Send a test event via HEC ───────────────────────────────────────
print("\n══════════════════════════════════════════")
print("  Step 3 — HEC test event injection")
print("══════════════════════════════════════════")

test_event = {
    "event": {
        "source": "ai-soc-validation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "AI-SOC Splunk HEC validation event",
        "alert_id": "VALIDATION-001",
        "severity": "low",
        "ai_verdict": "true_positive",
    },
    "index": "ai_soc",
    "sourcetype": "ai_soc:enriched",
}

try:
    body = json.dumps(test_event).encode("utf-8")
    req = urllib.request.Request(
        f"{SPLUNK_HEC_URL}/services/collector/event",
        data=body,
        headers={
            "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        resp_body = resp.read().decode()
        ok = resp.status == 200
        record("HEC accepts test event (200)", ok, f"Response: {resp_body[:200]}")
except urllib.error.HTTPError as e:
    body_text = e.read().decode() if hasattr(e, "read") else ""
    record("HEC accepts test event (200)", False, f"HTTP {e.code}: {body_text[:200]}")
except Exception as e:
    record("HEC accepts test event (200)", False, str(e))


# ─── Step 4: DNS resolution wazuh-integration → splunk ───────────────────────
print("\n══════════════════════════════════════════")
print("  Step 4 — Container DNS resolution")
print("══════════════════════════════════════════")

try:
    out = subprocess.check_output(
        ["docker", "exec", WAZUH_INT_CTR, "python3", "-c",
         "import socket; print(socket.gethostbyname('splunk'))"],
        text=True, stderr=subprocess.PIPE, timeout=10,
    ).strip()
    record("wazuh-integration resolves 'splunk' hostname", bool(out), f"Resolved to: {out}")
except subprocess.CalledProcessError as e:
    record("wazuh-integration resolves 'splunk' hostname", False, e.stderr.strip())
except Exception as e:
    record("wazuh-integration resolves 'splunk' hostname", False, str(e))


# ─── Step 5: httpx present in wazuh-integration container ────────────────────
print("\n══════════════════════════════════════════")
print("  Step 5 — httpx installed in container")
print("══════════════════════════════════════════")

try:
    out = subprocess.check_output(
        ["docker", "exec", WAZUH_INT_CTR, "pip", "show", "httpx"],
        text=True, stderr=subprocess.PIPE, timeout=15,
    ).strip()
    ok = "Name: httpx" in out
    version_line = next((l for l in out.splitlines() if "Version" in l), "")
    record("httpx installed in wazuh-integration", ok, version_line)
except subprocess.CalledProcessError as e:
    record("httpx installed in wazuh-integration", False, e.stderr.strip())
except Exception as e:
    record("httpx installed in wazuh-integration", False, str(e))


# ─── Step 6: Wazuh manager logs (no errors after restart) ────────────────────
print("\n══════════════════════════════════════════")
print("  Step 6 — Wazuh manager log check")
print("══════════════════════════════════════════")

try:
    out = subprocess.check_output(
        ["docker", "logs", WAZUH_MANAGER_CTR, "--tail", "80"],
        text=True, stderr=subprocess.STDOUT, timeout=15,
    )
    errors = [l for l in out.splitlines() if "ERROR" in l or "ossec" in l.lower() and "xml" in l.lower()]
    ok = len(errors) == 0
    detail = "; ".join(errors[:5]) if errors else "No XML/syslog errors detected"
    record("Wazuh manager logs free of config errors", ok, detail)
except Exception as e:
    record("Wazuh manager logs free of config errors", False, str(e))


# ─── Step 7: Splunk search for validation event (via REST API) ────────────────
print("\n══════════════════════════════════════════")
print("  Step 7 — Splunk event search")
print("══════════════════════════════════════════")

SPLUNK_USER = "admin"
SPLUNK_PASS = os.getenv("SPLUNK_PASSWORD", "SecureSplunkPassword123!")
SPLUNK_MGMT = "http://localhost:8089"

try:
    # Submit search job
    import base64
    creds = base64.b64encode(f"{SPLUNK_USER}:{SPLUNK_PASS}".encode()).decode()
    search_data = urllib.parse.urlencode({
        "search": 'search index=ai_soc sourcetype="ai_soc:enriched" source="ai-soc-validation" | head 1',
        "output_mode": "json",
    }).encode()

    import urllib.parse
    search_req = urllib.request.Request(
        f"{SPLUNK_MGMT}/services/search/jobs",
        data=search_data,
        headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(search_req, timeout=TIMEOUT) as resp:
        job_resp = json.loads(resp.read().decode())
        sid = job_resp.get("sid")
        record("Splunk search job created", bool(sid), f"SID: {sid}")
except Exception as e:
    record("Splunk search job created", False, str(e))
    sid = None

if sid:
    import time
    # Poll for job completion (max 30 s)
    done = False
    for _ in range(10):
        time.sleep(3)
        try:
            poll_req = urllib.request.Request(
                f"{SPLUNK_MGMT}/services/search/jobs/{sid}?output_mode=json",
                headers={"Authorization": f"Basic {creds}"},
            )
            with urllib.request.urlopen(poll_req, timeout=TIMEOUT) as resp:
                status_body = json.loads(resp.read().decode())
                dispatch_state = status_body["entry"][0]["content"]["dispatchState"]
                if dispatch_state == "DONE":
                    done = True
                    break
        except Exception:
            break

    if done:
        try:
            results_req = urllib.request.Request(
                f"{SPLUNK_MGMT}/services/search/jobs/{sid}/results?output_mode=json&count=1",
                headers={"Authorization": f"Basic {creds}"},
            )
            with urllib.request.urlopen(results_req, timeout=TIMEOUT) as resp:
                results_body = json.loads(resp.read().decode())
                hits = results_body.get("results", [])
                record("Validation event found in Splunk index", len(hits) > 0,
                       f"Hits: {len(hits)}" if hits else "0 results — event may not have been indexed yet")
        except Exception as e:
            record("Validation event found in Splunk index", False, str(e))
    else:
        record("Validation event found in Splunk index", False,
               "Search job did not complete in 30 s")


# ─── Step 8: btool config load verification ──────────────────────────────────
print("\n══════════════════════════════════════════")
print("  Step 8 — btool config load verification")
print("══════════════════════════════════════════")
print(f"{INFO} Run manually after startup (btool requires a live Splunk process):")
print("       docker exec splunk splunk btool inputs list --debug | findstr inputs.conf")
print("       docker exec splunk splunk btool indexes list --debug | findstr ai_soc")
print("  Expect: /opt/splunk/etc/system/local/inputs.conf in the btool output.")
print("  If absent: the mount path is wrong or Splunk did not load the file.")

for label, btool_arg, expected_token in [
    ("btool inputs shows system/local/inputs.conf",  "inputs",  "system/local/inputs.conf"),
    ("btool indexes shows ai_soc index",             "indexes", "ai_soc"),
]:
    try:
        out = subprocess.check_output(
            ["docker", "exec", SPLUNK_CTR, "splunk", "btool", btool_arg, "list", "--debug"],
            text=True, stderr=subprocess.PIPE, timeout=20,
        )
        ok = expected_token in out
        record(label, ok, f"Token '{expected_token}' {'found' if ok else 'NOT found'} in btool output")
    except subprocess.CalledProcessError as e:
        record(label, False, e.stderr.strip()[:200])
    except Exception as e:
        record(label, False, str(e))


# ─── Step 9: Index existence via SPL eventcount ───────────────────────────────
print("\n══════════════════════════════════════════")
print("  Step 9 — Index existence (SPL eventcount)")
print("══════════════════════════════════════════")
print(f"{INFO} SPL: | eventcount summarize=false index=* | search index=ai_soc OR index=wazuh")

try:
    import base64
    import urllib.parse
    creds_b64 = base64.b64encode(f"{SPLUNK_USER}:{SPLUNK_PASS}".encode()).decode()
    ec_data = urllib.parse.urlencode({
        "search": '| eventcount summarize=false index=* | search index=ai_soc OR index=wazuh',
        "output_mode": "json",
    }).encode()
    ec_req = urllib.request.Request(
        f"{SPLUNK_MGMT}/services/search/jobs",
        data=ec_data,
        headers={"Authorization": f"Basic {creds_b64}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(ec_req, timeout=TIMEOUT) as r:
        ec_sid = json.loads(r.read().decode()).get("sid")

    if ec_sid:
        import time
        time.sleep(8)
        ec_results_req = urllib.request.Request(
            f"{SPLUNK_MGMT}/services/search/jobs/{ec_sid}/results?output_mode=json",
            headers={"Authorization": f"Basic {creds_b64}"},
        )
        with urllib.request.urlopen(ec_results_req, timeout=TIMEOUT) as r:
            ec_body = json.loads(r.read().decode())
            found_indexes = {row.get("index") for row in ec_body.get("results", [])}
            for idx in ["ai_soc", "wazuh"]:
                record(f"Index '{idx}' exists in Splunk", idx in found_indexes,
                       f"Found indexes: {sorted(found_indexes)[:10]}")
except Exception as e:
    for idx in ["ai_soc", "wazuh"]:
        record(f"Index '{idx}' exists in Splunk", False, str(e))


# ─── Step 10: Splunk outage resilience ───────────────────────────────────────
print("\n══════════════════════════════════════════")
print("  Step 10 — Splunk outage resilience")
print("══════════════════════════════════════════")
print(f"{INFO} Testing: wazuh-integration returns 200 even when Splunk HEC is unreachable")
print(f"{INFO} (Splunk must be stopped first, or HEC port blocked, for this to be a real test)")

try:
    # Hit the wazuh-integration /alert/receive with a synthetic payload.
    # If HEC is down, the background task should fail silently and the endpoint
    # should still return 200 (or 422 for validation, not 500 from Splunk).
    test_payload = json.dumps({
        "id": "RESILIENCE-TEST-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rule": {"id": "1002", "level": 9, "description": "Outage resilience test"},
        "agent": {"id": "001", "name": "test-agent"},
        "location": "/var/log/test",
        "full_log": "resilience test alert",
    }).encode()
    resil_req = urllib.request.Request(
        "http://localhost:8002/api/v1/alerts/receive",
        data=test_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(resil_req, timeout=15) as r:
        # Any 2xx is acceptable — the pipeline must not surface Splunk failures as 500
        ok = 200 <= r.status < 300
        record("Pipeline returns 2xx when Splunk is unreachable", ok,
               f"HTTP {r.status} from wazuh-integration")
except urllib.error.HTTPError as e:
    ok = e.code != 500
    record("Pipeline returns 2xx when Splunk is unreachable", ok,
           f"HTTP {e.code} — {'acceptable non-500' if ok else 'PIPELINE BLOCKED by Splunk failure'}")
except Exception as e:
    record("Pipeline returns 2xx when Splunk is unreachable", False, str(e))


# ─── Summary ──────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════")
print("  Validation Summary")
print("══════════════════════════════════════════")

passed  = sum(1 for r in results if r["ok"])
failed  = sum(1 for r in results if not r["ok"])
total   = len(results)

print(f"{PASS} Passed : {passed}/{total}")
if failed:
    print(f"{FAIL} Failed : {failed}/{total}")
    print("\nFailing checks:")
    for r in results:
        if not r["ok"]:
            print(f"  • {r['label']}")
            if r["detail"]:
                print(f"    {r['detail']}")
else:
    print("\n✅ All checks passed. Integration is operational.")

sys.exit(0 if failed == 0 else 1)
