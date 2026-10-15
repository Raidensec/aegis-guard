from __future__ import annotations

from html import escape
from pathlib import Path
import math
import re


OUT = Path(r"C:\Users\ENG_AHMAD_ESSAM\Desktop\AI_SOC_Diagrams\thesis_svg")
W, H = 1618, 1000


class SVG:
    def __init__(self, title: str):
        self.title = title
        self.items: list[str] = []
        self.defs: list[str] = []
        self.add_defs()

    def add_defs(self) -> None:
        self.defs.append(
            """
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#111111"/>
            </marker>
            <marker id="arrow-blue" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#2F5597"/>
            </marker>
            """
        )

    def text(self, x, y, text, size=26, weight="400", anchor="middle", fill="#111111",
             max_width=None, line_height=1.25, italic=False):
        text = str(text)
        if max_width:
            lines = wrap(text, max_width, size)
        else:
            lines = text.split("\n")
        style = f"font-size:{size}px;font-weight:{weight};font-style:{'italic' if italic else 'normal'}"
        if len(lines) == 1:
            self.items.append(
                f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" style="{style}">{escape(lines[0])}</text>'
            )
            return
        dy = 0
        for i, line in enumerate(lines):
            self.items.append(
                f'<text x="{x}" y="{y + dy}" text-anchor="{anchor}" fill="{fill}" style="{style}">{escape(line)}</text>'
            )
            dy += size * line_height

    def rect(self, x, y, w, h, fill="#ffffff", stroke="#111111", sw=2, rx=0):
        self.items.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def line(self, x1, y1, x2, y2, stroke="#111111", sw=2, arrow=False, dash=None):
        marker = ' marker-end="url(#arrow)"' if arrow and stroke != "#2F5597" else ""
        marker = ' marker-end="url(#arrow-blue)"' if arrow and stroke == "#2F5597" else marker
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.items.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{marker}{dash_attr}/>'
        )

    def path(self, d, stroke="#111111", sw=2, fill="none", arrow=False, dash=None):
        marker = ' marker-end="url(#arrow)"' if arrow and stroke != "#2F5597" else ""
        marker = ' marker-end="url(#arrow-blue)"' if arrow and stroke == "#2F5597" else marker
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.items.append(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{marker}{dash_attr}/>'
        )

    def circle(self, cx, cy, r, fill="#ffffff", stroke="#111111", sw=2):
        self.items.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def ellipse(self, cx, cy, rx, ry, fill="#ffffff", stroke="#111111", sw=2):
        self.items.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def title_block(self, subtitle: str | None = None):
        self.text(W / 2, 70, self.title, 36, "700")
        if subtitle:
            self.text(W / 2, 110, subtitle, 21, "400", fill="#555555")
        self.line(110, 140, W - 110, 140, stroke="#777777", sw=1)

    def save(self, path: Path):
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(self.title)}">
  <title>{escape(self.title)}</title>
  <defs>{''.join(self.defs)}</defs>
  <rect width="100%" height="100%" fill="#ffffff"/>
  <g font-family="Arial, Helvetica, sans-serif">
    {''.join(self.items)}
  </g>
</svg>
'''
        path.write_text(svg, encoding="utf-8")


def wrap(text: str, max_width: float, size: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line: list[str] = []
    approx = size * 0.54
    for word in words:
        trial = " ".join(line + [word])
        if len(trial) * approx <= max_width or not line:
            line.append(word)
        else:
            lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    return lines


def box(s: SVG, x, y, w, h, title, body="", fill="#ffffff", stroke="#111111", title_size=23, body_size=18):
    s.rect(x, y, w, h, fill=fill, stroke=stroke, sw=2, rx=6)
    title_lines = wrap(str(title), w - 30, title_size)
    s.text(x + w / 2, y + 34, title, title_size, "700", max_width=w - 30)
    if body:
        body_y = y + 66 + max(0, len(title_lines) - 1) * title_size * 1.2
        s.text(x + w / 2, body_y, body, body_size, "400", fill="#333333", max_width=w - 32)


def pill(s: SVG, x, y, w, h, text, fill="#F3F6FA", stroke="#111111", size=20):
    s.rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.7, rx=h / 2)
    s.text(x + w / 2, y + h / 2 + size * 0.35, text, size, "600", max_width=w - 20)


def flow_row(s: SVG, labels, y=410, x0=110, gap=38, bw=None, bh=126, bodies=None, fill="#F7F9FC"):
    n = len(labels)
    bw = bw or (W - 2 * x0 - gap * (n - 1)) / n
    xs = [x0 + i * (bw + gap) for i in range(n)]
    for i, (x, label) in enumerate(zip(xs, labels)):
        box(s, x, y, bw, bh, label, bodies[i] if bodies else "", fill=fill)
        if i < n - 1:
            s.line(x + bw + 8, y + bh / 2, xs[i + 1] - 10, y + bh / 2, arrow=True, sw=2)
    return xs, bw


def table(s: SVG, x, y, w, h, headers, rows, col_widths=None, header_fill="#EAF0F7", size=18):
    ncols = len(headers)
    nrows = len(rows) + 1
    col_widths = col_widths or [w / ncols] * ncols
    row_h = h / nrows
    s.rect(x, y, w, h, fill="#ffffff", stroke="#111111", sw=2, rx=0)
    cx = x
    for c, cw in enumerate(col_widths):
        if c > 0:
            s.line(cx, y, cx, y + h, sw=1.2, stroke="#555555")
        s.rect(cx, y, cw, row_h, fill=header_fill, stroke="none", sw=0)
        s.text(cx + cw / 2, y + row_h / 2 + 7, headers[c], size, "700", max_width=cw - 16)
        cx += cw
    for r in range(1, nrows):
        yy = y + r * row_h
        s.line(x, yy, x + w, yy, sw=1.2, stroke="#555555")
        cx = x
        for c, cw in enumerate(col_widths):
            s.text(cx + cw / 2, yy + row_h / 2 + 7, rows[r - 1][c], size - 1, "400", max_width=cw - 18)
            cx += cw


def fig01():
    s = SVG("Aegis Guard System Architecture")
    s.title_block("Layered view of sensing, analytics, orchestration, and operator interfaces")
    layers = [
        ("Telemetry Sources", "Wazuh agents, Suricata, Zeek, host and network logs"),
        ("Ingestion and SIEM Core", "Wazuh Manager, Indexer, Dashboard, Integration Service"),
        ("AI Analysis Services", "Triage LLM, RAG, ML inference, correlation engine"),
        ("Decision and Response", "Rule generation, D3FEND mapping, response orchestrator"),
        ("Visibility and Feedback", "Analyst feedback, Grafana, Prometheus, Alertmanager"),
    ]
    y = 185
    for i, (name, body) in enumerate(layers):
        fill = "#F7F9FC" if i % 2 == 0 else "#FFFFFF"
        s.rect(140, y, 1338, 118, fill=fill, stroke="#111111", rx=6)
        s.text(250, y + 52, name, 24, "700", anchor="start")
        s.text(625, y + 52, body, 22, "400", anchor="start", max_width=760)
        if i < len(layers) - 1:
            s.line(W / 2, y + 126, W / 2, y + 158, arrow=True)
        y += 145
    return s


def fig02():
    s = SVG("Wazuh Alert Filtering Matrix")
    s.title_block("Rule severity is converted into routing decisions before AI enrichment")
    headers = ["Level", "Meaning", "Routing", "Typical Action"]
    rows = [
        ["0-3", "Low value", "Store only", "No AI call"],
        ["4-7", "Suspicious", "Queue for review", "Context lookup"],
        ["8-11", "High severity", "AI triage", "Incident candidate"],
        ["12-15", "Critical", "Escalate", "Immediate response plan"],
    ]
    table(s, 130, 210, 1358, 460, headers, rows, [190, 370, 350, 448], size=22)
    s.text(W/2, 760, "Design intent: reduce noise before expensive local-model analysis.", 24, "600", fill="#2F5597")
    return s


def fig03():
    s = SVG("ML Inference Pipeline")
    s.title_block("Network-flow features are transformed into a calibrated prediction")
    labels = ["Raw Flow", "Feature Order", "Scaler", "Model", "Prediction", "SOC Use"]
    bodies = ["Zeek / CICFlow fields", "77 trained feature names", "Artifact-aligned transform", "Random Forest / XGBoost", "Class and confidence", "Triage and correlation"]
    flow_row(s, labels, y=385, bodies=bodies, bh=160)
    s.line(225, 650, 1395, 650, stroke="#2F5597", sw=3, arrow=True)
    s.text(810, 705, "Invariant: inference payload must match the saved training feature order.", 23, "600", fill="#2F5597")
    return s


def fig04():
    s = SVG("Alert Triage Prompt Schema")
    s.title_block("The LLM receives structured fields and must return a bounded JSON decision")
    box(s, 130, 245, 420, 330, "Input Alert", "rule description\nrule level\nsource/destination\nraw log", fill="#F7F9FC")
    box(s, 600, 245, 420, 330, "Controlled Prompt", "role instruction\nschema contract\nfew-shot policy\nretrieved context", fill="#FFFFFF")
    box(s, 1070, 245, 420, 330, "JSON Output", "severity\ncategory\nconfidence\nIOCs\nrecommendations", fill="#F7F9FC")
    s.line(560, 410, 590, 410, arrow=True)
    s.line(1030, 410, 1060, 410, arrow=True)
    s.text(W/2, 715, "Output validation prevents free-form text from entering downstream automation.", 23, "600", fill="#2F5597")
    return s


def fig05():
    s = SVG("RAG Knowledge-Base Distribution")
    s.title_block("Separate collections preserve source meaning while sharing one retrieval interface")
    center_x, center_y = 809, 515
    s.circle(center_x, center_y, 112, fill="#EAF0F7")
    s.text(center_x, center_y - 8, "ChromaDB", 25, "700")
    s.text(center_x, center_y + 28, "Vector Index", 20, "400")
    nodes = [
        ("MITRE ATT&CK", 345, 265, 160, 48, -92, -68),
        ("D3FEND", 1273, 265, -160, 48, 92, -68),
        ("Sigma Rules", 345, 705, 160, -48, -92, 68),
        ("Runbooks", 1273, 705, -160, -48, 92, 68),
        ("Project Docs", 809, 835, 0, -56, 0, 112),
    ]
    for label, x, y, sx, sy, ex, ey in nodes:
        box(s, x - 160, y - 55, 320, 110, label, "embedded chunks", fill="#FFFFFF")
        s.line(x + sx, y + sy, center_x + ex, center_y + ey, arrow=True)
    return s


def fig06():
    s = SVG("Analyst Feedback Loop")
    s.title_block("Human labels close the loop between triage decisions and model improvement")
    labels = ["AI Decision", "Analyst Review", "Feedback Record", "Retraining Set", "Updated Model"]
    bodies = ["severity and label", "confirm or correct", "notes and true label", "validated examples", "champion/challenger"]
    flow_row(s, labels, y=380, bodies=bodies, bh=150)
    s.path("M 1320 585 C 1320 790, 290 790, 290 585", stroke="#2F5597", sw=3, arrow=True)
    s.text(810, 835, "Corrections are preserved as auditable evidence before changing production behavior.", 22, "600", fill="#2F5597")
    return s


def fig07():
    s = SVG("Markov Threat-State Model")
    s.title_block("Attack progress is represented as state transitions with probabilistic movement")
    main = [("Recon", 190), ("Initial Access", 500), ("Privilege Escalation", 810),
            ("Lateral Movement", 1120), ("Impact", 1430)]
    y = 365
    for name, x in main:
        s.circle(x, y, 82, fill="#F7F9FC")
        s.text(x, y + 8, name, 20, "700", max_width=132)
    for (name1, x1), (name2, x2), label in zip(main, main[1:], ["p01", "p12", "p23", "p34"]):
        s.line(x1 + 84, y, x2 - 88, y, arrow=True)
        s.text((x1 + x2) / 2, y - 25, label, 18, "600", fill="#555555")
    s.circle(810, 690, 92, fill="#FFFFFF")
    s.text(810, 698, "Contained", 21, "700")
    for x, label in [(500, "defense"), (810, "response"), (1120, "isolation")]:
        s.path(f"M {x} {450} C {x} 540, 810 560, 810 596", stroke="#2F5597", sw=2.5, arrow=True)
        s.text((x + 810) / 2, 535, label, 18, "600", fill="#2F5597")
    return s


def fig08():
    s = SVG("Monte Carlo Simulation Cycles")
    s.title_block("Repeated randomized runs estimate directional compromise and defense outcomes")
    box(s, 130, 235, 300, 150, "Scenario Inputs", "hosts, controls, vulnerabilities", fill="#F7F9FC")
    box(s, 500, 235, 300, 150, "Randomize", "attacker and environment", fill="#FFFFFF")
    box(s, 870, 235, 300, 150, "Run Agents", "campaign simulation", fill="#F7F9FC")
    box(s, 1240, 235, 300, 150, "Aggregate", "paths and confidence intervals", fill="#FFFFFF")
    for x in [430,800,1170]:
        s.line(x+10,310,x+60,310,arrow=True)
    for i in range(6):
        y = 520 + i * 45
        s.line(260, y, 1340, y, stroke="#777777", sw=1.5)
        s.circle(260 + i * 150, y, 12, fill="#2F5597", stroke="#2F5597")
        s.text(160, y+7, f"run {i+1}", 18, "600", anchor="start")
    s.text(W/2, 850, "The output is comparative research evidence, not a validated breach forecast.", 23, "700", fill="#2F5597")
    return s


def fig09():
    s = SVG("D3FEND Scoring Matrix")
    s.title_block("Candidate defenses are ranked by impact, safety, and confidence")
    headers = ["Countermeasure", "Impact", "Safety", "Confidence", "Decision"]
    rows = [
        ["Firewall deny", "High", "Medium", "High", "Auto-veto"],
        ["Host isolation", "High", "Low", "Medium", "Human"],
        ["Credential reset", "Medium", "Medium", "High", "Recommend"],
        ["Log enrichment", "Low", "High", "High", "Auto-safe"],
    ]
    table(s, 110, 220, 1398, 520, headers, rows, [360, 210, 210, 240, 378], size=21)
    return s


def fig10():
    s = SVG("Sigma Rule Lifecycle")
    s.title_block("Rules move from generated hypotheses to reviewed detection content")
    labels = ["Incident Pattern", "Draft Sigma", "Validate Fields", "Peer Review", "Deploy", "Monitor"]
    bodies = ["evidence cluster", "normalized YAML", "Wazuh mapping", "analyst approval", "rule repository", "false positives"]
    flow_row(s, labels, y=365, x0=70, gap=28, bw=225, bodies=bodies, bh=170)
    return s


def fig11():
    s = SVG("Champion-Challenger Model Governance")
    s.title_block("New models are compared against the production champion before promotion")
    box(s, 145, 260, 400, 180, "Champion", "current production model\nbaseline metrics", fill="#F7F9FC")
    box(s, 145, 560, 400, 180, "Challenger", "candidate artifact\nnew feedback data", fill="#FFFFFF")
    box(s, 760, 365, 430, 240, "Evaluation Gate", "accuracy\nfalse-positive rate\nlatency\nstability", fill="#EAF0F7")
    box(s, 1320, 385, 210, 200, "Promotion Decision", "only if safer", fill="#FFFFFF", title_size=21)
    s.line(545,350,750,430,arrow=True)
    s.line(545,650,750,535,arrow=True)
    s.line(1190,485,1310,485,arrow=True)
    s.path("M 1425 585 C 1425 815, 345 815, 345 742", stroke="#2F5597", sw=3, arrow=True)
    s.text(860, 850, "Rejected challengers return to training with analyst feedback.", 21, "700", fill="#2F5597")
    return s


def fig12():
    s = SVG("Incident Risk Matrix")
    s.title_block("Severity is interpreted as a combination of likelihood and impact")
    x0,y0,w,h = 285,220,940,600
    s.rect(x0,y0,w,h,fill="#ffffff",stroke="#111111",sw=2)
    for i in range(1,5):
        s.line(x0+i*w/5,y0,x0+i*w/5,y0+h,stroke="#777777",sw=1)
        s.line(x0,y0+i*h/5,x0+w,y0+i*h/5,stroke="#777777",sw=1)
    labels=["Low","Guarded","Elevated","High","Critical"]
    for i,l in enumerate(labels):
        s.text(x0+i*w/5+w/10,y0+h+42,l,18,"600")
        s.text(x0-52,y0+h-(i*w/5 if False else i*h/5)-h/10+8,l,18,"600")
    for i in range(5):
        for j in range(5):
            val=i+j
            fill="#FFFFFF" if val<3 else "#F3F6FA" if val<6 else "#EAF0F7"
            s.rect(x0+i*w/5,y0+(4-j)*h/5,w/5,h/5,fill=fill,stroke="#777777",sw=1)
            if val>=6:
                s.text(x0+i*w/5+w/10,y0+(4-j)*h/5+h/2+8,"Escalate",17,"700",fill="#2F5597")
    s.text(x0 + w / 2, y0 + h + 92, "Likelihood", 22, "700")
    s.text(110, y0 + h / 2, "Impact", 22, "700", anchor="middle")
    s.text(W/2, 930, "Shaded cells indicate incidents requiring escalation.", 22, "600", fill="#2F5597")
    return s


def fig13():
    s = SVG("Autonomy Tier Decision Policy")
    s.title_block("Execution authority increases only when risk and blast radius remain bounded")
    headers=["Tier","Risk Threshold","Blast Radius","Execution Behavior"]
    rows=[
        ["Observe","Any","None","Log only"],
        ["Recommend","Any","Any","Analyst decides"],
        ["Auto-safe","< 40%","Low","Execute automatically"],
        ["Auto-veto","< 75%","Medium","Execute after veto window"],
        ["Human-required",">= 75% or critical","High/Critical","Approval required"],
    ]
    table(s, 100, 215, 1418, 590, headers, rows, [290,310,300,518], size=21)
    s.line(250,845,1360,845,stroke="#2F5597",sw=4,arrow=True)
    s.text(805,900,"Autonomy increases left-to-right only when safety constraints are satisfied.",22,"700",fill="#2F5597")
    return s


def fig14():
    s = SVG("Model Retraining Workflow")
    s.title_block("Feedback becomes training data through a controlled production pipeline")
    labels = ["Production Alerts", "Analyst Feedback", "Label Generation", "Retraining Dataset", "Model Evaluation", "Redeploy"]
    bodies = ["Aegis Guard decisions", "true label and notes", "clean labels", "versioned examples", "champion/challenger", "approved artifact"]
    flow_row(s, labels, y=330, x0=70, gap=28, bw=225, bodies=bodies, bh=180)
    s.rect(360,650,900,120,fill="#F7F9FC",stroke="#111111",rx=6)
    s.text(810,700,"Governance checkpoint: no model update without metric comparison and rollback plan.",22,"700",fill="#2F5597",max_width=820)
    return s


def fig15():
    s = SVG("Attacker Archetypes")
    s.title_block("Simulation agents differ by objective, patience, and operational style")
    headers=["Archetype","Primary Objective","Typical Behavior","Simulation Role"]
    rows=[
        ["Opportunist","Easy access","Scans broadly","Baseline noise"],
        ["APT","Persistence","Slow multi-stage path","Advanced campaign"],
        ["Ransomware","Impact","Rapid privilege and encryption","Disruptive attack"],
        ["Insider","Misuse access","Policy bypass","Trusted-user risk"],
    ]
    table(s, 110, 230, 1398, 520, headers, rows, [250,340,390,418], size=20)
    return s


def fig16():
    s = SVG("Defender Operating Phases")
    s.title_block("Defender agents represent common SOC decision roles")
    lanes=[("SOC Analyst","Triage and confidence"),
           ("Incident Responder","Containment"),
           ("Threat Hunter","Related activity")]
    y=230
    for lane, desc in lanes:
        s.rect(120,y,250,170,fill="#EAF0F7",stroke="#111111",rx=6)
        s.text(245,y+70,lane,23,"700",max_width=210)
        steps=["Observe","Decide","Act","Verify"]
        xs, bw = flow_row(s, steps, y=y+20, x0=430, gap=22, bw=200, bh=130,
                          bodies=["telemetry","policy","response","outcome"], fill="#FFFFFF")
        box(s, 1330, y + 35, 190, 100, "Purpose", desc, fill="#FFFFFF", title_size=18, body_size=16)
        y+=220
    return s


def fig17():
    s = SVG("Prometheus Scrape Flow")
    s.title_block("Operational metrics are collected separately from security events")
    labels=["Services","Metrics Endpoint","Prometheus","Alertmanager","Grafana"]
    bodies=["FastAPI stack","latency and errors","time-series store","routing rules","dashboards"]
    flow_row(s, labels, y=365, x0=120, gap=42, bw=250, bodies=bodies, bh=170)
    s.text(W/2,690,"Observation plane: health and performance signals, not alert evidence.",22,"600",fill="#2F5597")
    return s


def fig18():
    s = SVG("ML Feature Groups")
    s.title_block("The 77 inference features can be understood as operational groups")
    center=(809,500)
    s.circle(*center,95,fill="#EAF0F7")
    s.text(center[0], center[1]-6, "77 Flow", 24, "700")
    s.text(center[0], center[1]+30, "Features", 24, "700")
    groups=[
        ("Duration",330,255,150,45,-82,-58),
        ("Packet Counts",810,205,0,50,0,-95),
        ("Byte Rates",1285,255,-150,45,82,-58),
        ("Flags",1285,650,-150,-45,82,58),
        ("IAT",810,810,0,-50,0,95),
        ("Header Stats",330,650,150,-45,-82,58),
    ]
    for label,x,y,sx,sy,ex,ey in groups:
        box(s,x-135,y-50,270,100,label,"feature subset",fill="#FFFFFF")
        s.line(x+sx,y+sy,center[0]+ex,center[1]+ey,arrow=True)
    return s


def fig19():
    s = SVG("RAG Distance Thresholds")
    s.title_block("Retrieval quality is gated before context enters the LLM prompt")
    x0,y=170,470
    s.line(x0,y,1440,y,sw=3,arrow=True)
    ticks=[("Exact",250),("Useful",560),("Weak",920),("Reject",1260)]
    for label,x in ticks:
        s.line(x,y-45,x,y+45,sw=2)
        s.text(x,y+88,label,22,"700")
    s.rect(190,340,500,80,fill="#EAF0F7",stroke="#111111",rx=6)
    s.text(440,390,"Include in prompt",22,"700")
    s.rect(930,340,360,80,fill="#FFFFFF",stroke="#111111",rx=6)
    s.text(1110,390,"Do not include",22,"700")
    s.text(W/2,730,"Lower vector distance means stronger semantic match.",22,"600",fill="#2F5597")
    return s


def fig20():
    s = SVG("Latency Budget by Processing Phase")
    s.title_block("Expected response time is allocated across the Aegis Guard workflow")
    phases=[("Ingest",0,90),("Triage",90,310),("RAG",310,430),("Correlation",430,610),("Response Plan",610,830)]
    x0,y0,w=210,390,1180
    s.line(x0,y0,x0+w,y0,sw=3)
    for name,start,end in phases:
        x=x0+start/830*w; ww=(end-start)/830*w
        s.rect(x,y0-58,ww,116,fill="#F7F9FC",stroke="#111111",rx=4)
        s.text(x+ww/2,y0-10,name,19,"700",max_width=ww-10)
        s.text(x+ww/2,y0+28,f"{end-start} ms",18,"400")
    s.text(W/2,660,"Budgeting makes slow components visible before they affect analyst workflow.",22,"600",fill="#2F5597")
    return s


def fig21():
    s = SVG("MITRE Tactic Coverage")
    s.title_block("Coverage is shown as capability presence rather than decorative heat")
    tactics=["Recon","Initial Access","Execution","Persistence","Privilege","Defense Evasion","Credential","Discovery","Lateral","Impact"]
    x0,y0=125,250
    for i,t in enumerate(tactics):
        x=x0+(i%5)*280; y=y0+(i//5)*230
        s.rect(x,y,230,140,fill="#F7F9FC" if i%2==0 else "#FFFFFF",stroke="#111111",rx=6)
        s.text(x+115,y+55,t,21,"700",max_width=200)
        s.text(x+115,y+96,"rules + AI context",17,"400")
    return s


def fig22():
    s = SVG("Swarm Simulation Scaling")
    s.title_block("Leader/follower execution reduces repeated work across many agents")
    box(s,110,390,300,180,"Leader Run","full reasoning trajectory",fill="#EAF0F7")
    followers=[(610,250,"Follower 1"),(610,430,"Follower 2"),(610,610,"Follower 3")]
    for x,y,label in followers:
        box(s,x,y,270,125,label,"sampled variation",fill="#FFFFFF")
        s.line(410,480,x-10,y+62,arrow=True)
    box(s,1120,390,360,180,"Aggregate Results","paths, host risk, confidence intervals",fill="#F7F9FC")
    for x,y,label in followers:
        s.line(x+270,y+62,1110,480,arrow=True)
    s.text(W/2,820,"The leader defines the campaign logic; followers explore scalable variations.",22,"700",fill="#2F5597")
    return s


def fig23():
    s = SVG("Agreement Validation")
    s.title_block("AI labels are compared with analyst ground truth before trust is increased")
    headers=["Case Type","LLM Label","Analyst Label","Outcome"]
    rows=[
        ["Agreement","Attack","Attack","reinforce"],
        ["False positive","Attack","Benign","correct model"],
        ["False negative","Benign","Attack","escalate review"],
        ["Uncertain","Low confidence","Any","human decision"],
    ]
    table(s,130,250,1358,500,headers,rows,[300,320,320,418],size=21)
    return s


def fig24():
    s = SVG("Adapter Success Flow")
    s.title_block("Response adapters must report execution and verification status")
    labels=["Plan Action","Check Policy","Execute Adapter","Verify Effect","Record Outcome"]
    bodies=["candidate defense","tier and scope","firewall / host / ticket","telemetry confirms","feedback store"]
    flow_row(s, labels, y=345, x0=90, gap=36, bw=270, bodies=bodies, bh=175)
    s.path("M 1140 555 C 1140 735, 700 735, 700 555", stroke="#2F5597", sw=3, arrow=True)
    s.text(920,790,"Failed verification returns the action to planning.",22,"700",fill="#2F5597")
    return s


def fig25():
    s = SVG("System Steady States")
    s.title_block("The platform alternates between monitoring, analysis, response, and recovery")
    states=[("Monitor",360,300),("Analyze",1050,300),("Respond",1050,650),("Recover",360,650)]
    for name,x,y in states:
        box(s,x-145,y-65,290,130,name,"steady state",fill="#F7F9FC")
    s.line(505,300,895,300,arrow=True)
    s.line(1050,365,1050,585,arrow=True)
    s.line(905,650,505,650,arrow=True)
    s.line(360,585,360,365,arrow=True)
    s.text(705,260,"incident event",21,"700",fill="#2F5597")
    s.text(1220,485,"response action",21,"700",fill="#2F5597",anchor="start")
    s.text(705,705,"outcome verified",21,"700",fill="#2F5597")
    s.text(200,485,"return to monitoring",21,"700",fill="#2F5597",anchor="start",max_width=130)
    return s


def fig26():
    s = SVG("Attack Propagation Path")
    s.title_block("Host compromise is represented as a path through reachable assets")
    hosts=[
        ("Internet",170,360),("VPN",395,360),("Web",620,360),("App",845,360),
        ("DB",1070,360),("Backup",1295,360),("Workstation",395,650),("Domain",845,650),
    ]
    pos={name:(x,y) for name,x,y in hosts}
    for name,x,y in hosts:
        s.rect(x-82,y-45,164,90,fill="#FFFFFF",stroke="#111111",rx=6)
        s.text(x,y+7,name,20,"700")
    for a,b in [("Internet","VPN"),("VPN","Web"),("Web","App"),("App","DB"),("DB","Backup")]:
        x1,y1=pos[a]; x2,y2=pos[b]
        s.line(x1+82,y1,x2-86,y2,arrow=True)
    s.line(pos["Workstation"][0]+82,pos["Workstation"][1],pos["Domain"][0]-86,pos["Domain"][1],arrow=True)
    s.path("M 845 405 C 845 505, 845 530, 845 602", arrow=True)
    s.text(902,535,"privilege path",18,"600",fill="#2F5597",anchor="start")
    s.text(W/2,870,"Path frequency helps prioritize monitoring and segmentation.",22,"600",fill="#2F5597")
    return s


def fig27():
    s = SVG("OWASP Coverage Requirements")
    s.title_block("API security tests map to standard web-risk categories")
    cats=["Auth","Access Control","Input Validation","Logging","Rate Limit","Secrets","Config","Error Handling"]
    x0,y0=150,260
    for i,c in enumerate(cats):
        x=x0+(i%4)*340; y=y0+(i//4)*235
        s.rect(x,y,280,145,fill="#F7F9FC",stroke="#111111",rx=6)
        s.text(x+140,y+58,c,22,"700")
        s.text(x+140,y+98,"test required",18,"400")
    return s


def fig28():
    s = SVG("Auto-Veto Window Sequence")
    s.title_block("Medium-blast actions wait for analyst veto before execution")
    actors=["Orchestrator","Analyst","Adapter","Monitoring"]
    y0=230
    for i,a in enumerate(actors):
        x=220+i*380
        s.text(x,y0,a,23,"700")
        s.line(x,y0+30,x,850,stroke="#777777",sw=1.5,dash="6 6")
    msgs=[(0,1,330,"propose action"),(1,0,430,"no veto before timeout"),(0,2,540,"execute"),(2,3,650,"emit outcome"),(3,0,760,"verification result")]
    for a,b,y,label in msgs:
        x1=220+a*380; x2=220+b*380
        s.line(x1,y,x2,y,arrow=True,stroke="#2F5597" if a==0 else "#111111")
        s.text((x1+x2)/2,y-15,label,19,"600")
    return s


def fig29():
    s = SVG("ChromaDB Embedding Space")
    s.title_block("Retrieved context is selected by semantic proximity to the alert query")
    s.rect(180,210,1250,650,fill="#FFFFFF",stroke="#111111",rx=6)
    points=[(420,360,"MITRE"),(520,420,"MITRE"),(760,310,"D3FEND"),(840,370,"D3FEND"),(1120,610,"Runbook"),(1180,680,"Runbook"),(620,670,"Sigma"),(700,730,"Sigma")]
    for x,y,l in points:
        s.circle(x,y,16,fill="#F7F9FC")
        s.text(x+25,y+7,l,17,"400",anchor="start")
    s.circle(610,500,22,fill="#2F5597",stroke="#2F5597")
    s.text(640,508,"Alert query",20,"700",anchor="start",fill="#2F5597")
    s.circle(610,500,190,fill="none",stroke="#2F5597",sw=2)
    s.text(W/2,925,"Only nearby chunks are eligible for prompt context.",22,"600",fill="#2F5597")
    return s


def fig30():
    s = SVG("Incident Processing Lifecycle")
    s.title_block("Single workflow from alert intake to verified defensive outcome")
    labels=["Ingestion","Triage","Planning","Execution","Verification"]
    bodies=["collect and normalize alerts","score severity and confidence","select safe response options","apply approved action","confirm outcome and learn"]
    xs,bw=flow_row(s, labels, y=330, bodies=bodies, bh=190)
    for i, x in enumerate(xs):
        s.text(x+bw/2, 590, f"Stage {i+1}", 18, "600", fill="#555555")
    s.text(W/2,760,"Control loop: verification results update feedback and future response planning.",23,"700",fill="#2F5597")
    return s


FIGS = [
    ("fig01_system_architecture.svg", fig01),
    ("fig02_wazuh_filtering_matrix.svg", fig02),
    ("fig03_ml_inference_pipeline.svg", fig03),
    ("fig04_triage_prompt_schema.svg", fig04),
    ("fig05_rag_db_distribution.svg", fig05),
    ("fig06_analyst_feedback_loop.svg", fig06),
    ("fig07_markov_threat_states.svg", fig07),
    ("fig08_monte_carlo_cycles.svg", fig08),
    ("fig09_d3fend_scoring_matrix.svg", fig09),
    ("fig10_sigma_rule_lifecycle.svg", fig10),
    ("fig11_champion_challenger_models.svg", fig11),
    ("fig12_incident_risk_matrix.svg", fig12),
    ("fig13_autonomy_tier_rules.svg", fig13),
    ("fig14_retraining_workflow.svg", fig14),
    ("fig15_attacker_archetypes.svg", fig15),
    ("fig16_defender_phases.svg", fig16),
    ("fig17_prometheus_scrape_flow.svg", fig17),
    ("fig18_ml_features_groups.svg", fig18),
    ("fig19_rag_distance_thresholds.svg", fig19),
    ("fig20_latency_budget.svg", fig20),
    ("fig21_mitre_tactic_coverage.svg", fig21),
    ("fig22_swarm_scaling.svg", fig22),
    ("fig23_agreement_validation.svg", fig23),
    ("fig24_adapter_success_flow.svg", fig24),
    ("fig25_system_steady_states.svg", fig25),
    ("fig26_attack_propagation_path.svg", fig26),
    ("fig27_owasp_coverage_requirements.svg", fig27),
    ("fig28_veto_window_sequence.svg", fig28),
    ("fig29_chromadb_embedding_space.svg", fig29),
    ("fig30_incident_lifecycle.svg", fig30),
]


def slug_to_title(path: str) -> str:
    return re.sub(r"\s+", " ", path.replace(".svg", "").replace("_", " ")).title()


def write_report(files: list[Path]) -> None:
    report = OUT / "redesign_report.md"
    lines = [
        "# Aegis Guard Thesis Figure Redesign Report",
        "",
        "## Identified Weaknesses in the Original PNG Set",
        "",
        "- The original figures used presentation-style styling: bright colors, shadows, gradients, and decorative layouts.",
        "- Several diagrams buried the decision logic inside radial or decorative structures.",
        "- Text density and capitalization were inconsistent across figures.",
        "- Many diagrams depended on color distinctions that would weaken in grayscale printing.",
        "- Some workflows assumed system knowledge instead of explaining the process visually.",
        "",
        "## Redesign Rationale",
        "",
        "- All figures were rebuilt as editable SVG vector graphics with live text.",
        "- The visual system uses one font family, black/gray text, and one muted blue accent.",
        "- Layouts were chosen by information purpose: architecture maps, process flows, matrices, state diagrams, sequence diagrams, and policy tables.",
        "- Decorative effects were removed to prioritize thesis readability and grayscale robustness.",
        "- Each figure is on a 1618 x 1000 golden-ratio landscape canvas for consistent placement in the report.",
        "",
        "## Output Files",
        "",
    ]
    for f in files:
        lines.append(f"- `{f.name}`")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index(files: list[Path]) -> None:
    html = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>Aegis Guard Thesis SVG Diagrams</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;color:#111} .grid{display:grid;grid-template-columns:1fr;gap:28px} figure{margin:0;border:1px solid #ccc;padding:12px} img{width:100%;height:auto} figcaption{font-weight:700;margin:8px 0}</style>",
        "</head><body><h1>Aegis Guard Thesis SVG Diagrams</h1><div class='grid'>",
    ]
    for f in files:
        html.append(f"<figure><figcaption>{escape(slug_to_title(f.name))}</figcaption><img src='{escape(f.name)}'></figure>")
    html.append("</div></body></html>")
    (OUT / "index.html").write_text("\n".join(html), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = []
    for name, fn in FIGS:
        svg = fn()
        path = OUT / name
        svg.save(path)
        files.append(path)
    write_report(files)
    write_index(files)
    print(f"Wrote {len(files)} SVG figures to {OUT}")


if __name__ == "__main__":
    main()
