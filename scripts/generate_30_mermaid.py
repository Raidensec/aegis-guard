"""
30 Unique Mermaid Diagrams Generator
AI-Augmented SOC

Generates 30 unique Mermaid.js diagrams describing various aspects of the Aegis Guard platform.
Exports each to an individual .mermaid file, and merges them into docs/project_mermaid_diagrams.md.
"""

import os
from pathlib import Path

# Dictionary of all 30 Mermaid diagrams
DIAGRAMS = {
    "fig01_system_architecture": {
        "title": "Figure 1: Aegis Guard Platform Architecture & Data Flow",
        "description": "High-level data flow from monitored Wazuh sensors through the webhook receiver, AI triage, RAG, and ML layers to the response orchestrator.",
        "code": """flowchart TB
    subgraph Inputs ["Detection & Collection"]
        A[Wazuh Agents] --> B[Wazuh Manager]
    end
    subgraph Ingest ["Ingestion Layer"]
        B --> C[Webhook Receiver :8002]
    end
    subgraph Analysis ["AI Analysis Layer"]
        C --> D[Alert Triage :8100]
        C --> E[RAG Service :8300]
        D <--> E
        D --> F[ML Inference :8500]
    end
    subgraph Incident ["Incident Intelligence"]
        D --> G[Correlation Engine :8600]
        E --> G
    end
    subgraph Action ["Response & Defense"]
        G --> H[Response Orchestrator :8800]
        H --> I[Sigma Rule Gen :8700]
    end"""
    },
    
    "fig02_wazuh_filtering_matrix": {
        "title": "Figure 2: Wazuh Alert Processing Tiers (Levels 0-15)",
        "description": "Decision matrix showing how Wazuh rules are routed or filtered based on severity level (Levels 0-6 are filtered out, Level 7 runs Triage only, Level 8+ runs Triage + RAG).",
        "code": """flowchart LR
    subgraph F [Filtered Out (Level < 7)]
        L0[Level 0]
        L1[Level 1]
        L2[Level 2]
        L3[Level 3]
        L4[Level 4]
        L5[Level 5]
        L6[Level 6]
    end
    subgraph T [AI Triage Only (Level 7)]
        L7[Level 7]
    end
    subgraph TR [AI Triage + RAG (Level >= 8)]
        L8[Level 8]
        L9[Level 9]
        L10[Level 10]
        L11[Level 11]
        L12[Level 12]
        L13[Level 13]
        L14[Level 14]
        L15[Level 15]
    end"""
    },

    "fig03_ml_inference_pipeline": {
        "title": "Figure 3: ML Network Flow Classification Pipeline",
        "description": "Linear pipeline transforming 77 raw network flow features through scaling and predictions into a BENIGN or ATTACK decision.",
        "code": """flowchart LR
    A[77 Flow Features] --> B[RobustScaler]
    B --> C{Ensemble Models}
    C -->|Random Forest| D[Binary Classifier]
    C -->|XGBoost| D
    C -->|Decision Tree| D
    D --> E[BENIGN vs ATTACK]"""
    },

    "fig04_triage_prompt_schema": {
        "title": "Figure 4: Structured Triage Prompt & Context Ingestion",
        "description": "Structured components within the LLM prompt block, outlining the context variables passed to ground the response.",
        "code": """flowchart TB
    subgraph PromptCard ["Prompt Context Card"]
        direction TB
        A["System Prompt: Security Expert & JSON Schema Instructions"]
        B["Alert Data Context: Source/Dest IPs, Ports, Rule Level, Logs"]
        C["ML Guidance Context: Robust Scale Vector & Prediction Probability"]
        D["RAG Grounding Context: MITRE Techniques, CVEs, Runbook Info"]
        A --- B --- C --- D
    end
    style A fill:#1e293b,stroke:#8b5cf6,stroke-width:2px
    style B fill:#1e293b,stroke:#3b82f6,stroke-width:2px
    style C fill:#1e293b,stroke:#06b6d4,stroke-width:2px
    style D fill:#1e293b,stroke:#f59e0b,stroke-width:2px"""
    },

    "fig05_rag_db_distribution": {
        "title": "Figure 5: Ingested Knowledge Sources in ChromaDB",
        "description": "Composition breakdown of security document chunks indexed within ChromaDB collections.",
        "code": """pie title ChromaDB Knowledge Base Composition
    "MITRE ATT&CK Techniques" : 45
    "NVD CVE Database" : 30
    "Incident Runbooks" : 15
    "Sigma Detection Rules" : 10"""
    },

    "fig06_analyst_feedback_loop": {
        "title": "Figure 6: Interactive Feedback & Retraining Loop",
        "description": "Workflow illustrating analyst corrections saving to database and feeding back into retraining pipelines to deploy champion models.",
        "code": """flowchart TB
    A[Alert Triage Output] --> B[Analyst Review & Edit]
    B --> C[(PostgreSQL Feedback DB)]
    C --> D[Retraining Pipeline]
    D --> E[Champion Model Promotion]
    E --> A"""
    },

    "fig07_markov_threat_states": {
        "title": "Figure 7: Markov Chain Attack Propagation Model",
        "description": "Directed state graph modeling attacker propagation through progressive kill-chain states with probabilities.",
        "code": """stateDiagram-v2
    [*] --> Reconnaissance
    Reconnaissance --> InitialAccess : p=0.65
    InitialAccess --> LateralMovement : p=0.45
    LateralMovement --> Exfiltration : p=0.50
    InitialAccess --> Mitigated : p=0.30
    LateralMovement --> Mitigated : p=0.40
    Exfiltration --> Mitigated : p=0.75
    Mitigated --> [*]"""
    },

    "fig08_monte_carlo_cycles": {
        "title": "Figure 8: Attacker-Defender Simulation Sequence",
        "description": "Sequence interaction diagram illustrating how Monte Carlo multi-agent runs resolve exploits and countermeasures.",
        "code": """sequenceDiagram
    autonumber
    participant Attacker as Attacker Agent
    participant Coord as Simulation Coordinator
    participant Defender as Defender Agent
    participant Env as Simulated Environment

    Attacker->>Coord: Submit attack action (exploit)
    Coord->>Env: Resolve vulnerability check
    Env-->>Coord: Return outcome (Compromised/Failed)
    Coord->>Defender: Notify of event alerts
    Defender->>Env: Execute defensive action (block IP)
    Env-->>Coord: Update host state map"""
    },

    "fig09_d3fend_scoring_matrix": {
        "title": "Figure 9: D3FEND Countermeasure Efficacy vs Safety Map",
        "description": "Quadrant chart mapping defensive countermeasures based on execution safety and mitigation efficacy.",
        "code": """quadrantChart
    title D3FEND Countermeasure Efficacy vs Safety
    x-axis "Low Safety" --> "High Safety"
    y-axis "Low Efficacy" --> "High Efficacy"
    quadrant-1 "High Efficacy / High Safety (Preferred)"
    quadrant-2 "High Efficacy / Low Safety (Caution)"
    quadrant-3 "Low Efficacy / Low Safety (Avoid)"
    quadrant-4 "Low Efficacy / High Safety (Informational)"
    Credential Revocation: [0.8, 0.85]
    IP Blocking: [0.75, 0.7]
    Host Isolation: [0.3, 0.9]
    Process Termination: [0.4, 0.8]
    Analyst Alerting: [0.95, 0.3]"""
    },

    "fig10_sigma_rule_lifecycle": {
        "title": "Figure 10: Sigma Detection Rule Validation Timeline",
        "description": "Gantt timeline of stages to compile, test, and deploy automatic Sigma detection rules.",
        "code": """gantt
    title Sigma Rule Validation & Deployment
    dateFormat  X
    axisFormat %d
    section Creation
    Rule Drafting            :active, a1, 0, 1
    Syntax Check             :after a1, 1d
    section Backtesting
    Query Compilation        :c1, after a1, 2d
    Historical Run           :after c1, 3d
    section Deployment
    SIEM Promotion           :after c1, 5d"""
    },

    "fig11_champion_challenger_models": {
        "title": "Figure 11: Champion vs. Challenger Model Structures",
        "description": "Class structure diagram comparing parameters and evaluation metrics between baseline and challenger models.",
        "code": """classDiagram
    class ModelEvaluator {
        +evaluateModel(dataset)
        +comparePerformance()
    }
    class XGBoostModel {
        +float accuracy = 0.998
        +float precision = 0.989
        +float recall = 0.991
        +float f1 = 0.990
    }
    class RandomForestModel {
        +float accuracy = 0.992
        +float precision = 0.982
        +float recall = 0.985
        +float f1 = 0.983
    }
    class DecisionTreeModel {
        +float accuracy = 0.975
        +float precision = 0.960
        +float recall = 0.965
        +float f1 = 0.962
    }
    ModelEvaluator --> XGBoostModel : Champion
    ModelEvaluator --> RandomForestModel : Challenger
    ModelEvaluator --> DecisionTreeModel : Baseline"""
    },

    "fig12_incident_risk_matrix": {
        "title": "Figure 12: Host Threat Exposure vs. Criticality Matrix",
        "description": "Quadrant classification map showing simulated host risks based on vulnerability levels and network value.",
        "code": """quadrantChart
    title Host Exposure vs. Criticality Map
    x-axis "Low Exposure --> High Exposure"
    y-axis "Low Criticality --> High Criticality"
    quadrant-1 "High Risk (Action Required)"
    quadrant-2 "High Criticality (Monitor Closely)"
    quadrant-3 "Low Risk"
    quadrant-4 "High Exposure / Low Criticality"
    host-domain-controller: [0.85, 0.95]
    host-database: [0.7, 0.9]
    host-webserver: [0.9, 0.6]
    host-jumpbox: [0.55, 0.75]
    host-workstation-01: [0.35, 0.3]
    host-workstation-02: [0.4, 0.25]"""
    },

    "fig13_autonomy_tier_rules": {
        "title": "Figure 13: Graduated Autonomy Tiers & Criteria",
        "description": "Mindmap structuring the 5 graduated levels of decision-making autonomy based on risk score thresholds.",
        "code": """mindmap
  root((Autonomy Tiers))
    Observe
      Log only
      Zero execution
      Blast radius 0
    Recommend
      Analyst decision
      Dashboard prompt
      Blast radius any
    Auto-Safe
      Low blast actions
      Immediate execution
      Risk threshold < 40%
    Auto-Veto
      Medium blast actions
      5m Grace period
      Risk threshold < 75%
    Human-Required
      Critical actions
      Explicit MFA/Auth
      Risk threshold > 75%"""
    },

    "fig14_retraining_gitgraph": {
        "title": "Figure 14: Model Retraining Versioning Flow",
        "description": "Git-graph mapping model promotions as code modifications on feedback branches merge into master.",
        "code": """gitGraph
    commit id: "v1.0.0-release"
    commit id: "collect-alerts"
    branch feedback-triage
    checkout feedback-triage
    commit id: "analyst-labels"
    commit id: "train-challenger"
    checkout main
    merge feedback-triage id: "v1.1.0-champion"
    commit id: "ml-server-reload"""
    },

    "fig15_attacker_archetypes": {
        "title": "Figure 15: Attacker Archetype Profile Map",
        "description": "Mindmap representing the distinct behaviors and capabilities of the 4 simulated attacker models.",
        "code": """mindmap
  root((Attacker Archetypes))
    Opportunist
      High speed
      Low stealth
      Wide targeting
      Basic exploits
    APT Campaign
      Low speed
      High stealth
      High persistence
      Custom payloads
    Ransomware
      High speed
      Low stealth
      High blast radius
      File encryption
    Insider Threat
      High access
      Medium stealth
      High targeted impact
      Credential abuse"""
    },

    "fig16_defender_phases": {
        "title": "Figure 16: Defender Activity Timeline",
        "description": "Reaction events and timelines showing latency steps for analytical agents and mitigations.",
        "code": """timeline
    title Defender Archetype Activity Timeline
    t = 0s : SOC Analyst Agent : Receives alert webhook, triggers triage LLM
    t = 5s : Incident Responder : Receives recommendation, starts veto grace timer
    t = 300s : Incident Responder : Grace timer expires, triggers block IP adapter
    t = 305s : Threat Hunter : Scraping network features, verifying baseline deviation"""
    },

    "fig17_prometheus_scrape_flow": {
        "title": "Figure 17: Service Observability Scraping Topology",
        "description": "Topology mapping Prometheus scraping endpoints across different distributed microservices.",
        "code": """flowchart TB
    subgraph Targets ["Monitored Services"]
        T1[triage-service :8100/metrics]
        T2[rag-service :8300/metrics]
        T3[ml-service :8500/metrics]
        T4[correlation-engine :8600/metrics]
        T5[feedback-service :8400/metrics]
        T6[response-orchestrator :8800/metrics]
    end
    Prom[Prometheus Server :9090]
    Graf[Grafana Dashboard :3000]

    T1 -->|HTTP Scrape| Prom
    T2 -->|HTTP Scrape| Prom
    T3 -->|HTTP Scrape| Prom
    T4 -->|HTTP Scrape| Prom
    T5 -->|HTTP Scrape| Prom
    T6 -->|HTTP Scrape| Prom

    Prom -->|Query API| Graf"""
    },

    "fig18_ml_features_mindmap": {
        "title": "Figure 18: 77 Network Flow Features Categorization",
        "description": "Mindmap structure showing top network feature subgroups used for ML binary classification.",
        "code": """mindmap
  root((77 Network Features))
    Packet-level
      Total Fwd Packets
      Total Bwd Packets
      Fwd Packet Length Std
      Bwd Packet Length Max
    IAT-level
      Flow IAT Mean
      Fwd IAT Max
      Bwd IAT Mean
    Throughput-level
      Flow Bytes/s
      Flow Packets/s
    Window-size-level
      Init Bwd Win Bytes
      Init Fwd Win Bytes
    Flags-level
      SYN Flag Count
      ACK Flag Count"""
    },

    "fig19_rag_distance_thresholds": {
        "title": "Figure 19: Cosine Distance Selection Thresholds",
        "description": "Decision flowchart detailing document inclusion or exclusion based on vector distance scores.",
        "code": """flowchart LR
    Query[Search Query] --> Dist{Cosine Distance}
    Dist -->|d < 0.30| Rel[Highly Relevant]
    Dist -->|0.30 <= d <= 0.38| Marg[Marginally Relevant]
    Dist -->|d > 0.38| Discard[Discarded Context]

    Rel -->|Include as Ground Truth| Prompt[LLM Triage Prompt]
    Marg -->|Include as Optional Context| Prompt
    Discard -->|Exclude| Prompt"""
    },

    "fig20_latency_gantt": {
        "title": "Figure 20: Webhook Processing Latency Budget Timeline",
        "description": "Gantt chart representing millisecond timeline budget distribution across ingestion components.",
        "code": """gantt
    title Webhook Latency Budget (Target: < 1.5s)
    dateFormat  X
    axisFormat %s
    section Ingestion
    Parse & Validate         :active, a1, 0, 20
    section AI Processing
    ML Inference Scrape      :active, a2, 20, 100
    RAG Vector Query         :active, a3, 100, 600
    LLM Triage Synthesis     :active, a4, 600, 1400
    section Storage
    PostgreSQL Logging       :active, a5, 1400, 1480"""
    },

    "fig21_mitre_tactic_coverage": {
        "title": "Figure 21: Ingested MITRE ATT&CK Tactics Map",
        "description": "Mindmap showing index tactics and key threat techniques mapped inside ChromaDB.",
        "code": """mindmap
  root((MITRE ATT&CK))
    Initial Access
      T1110 Brute Force
      T1190 Exploit Public-Facing App
    Execution
      T1059 Command and Scripting Interpreter
    Persistence
      T1098 Account Manipulation
    Defense Evasion
      T1027 Obfuscated Files
    Credential Access
      T1003 OS Credential Dumping
    Discovery
      T1046 Network Service Discovery
    Lateral Movement
      T1021 Remote Services"""
    },

    "fig22_swarm_scaling": {
        "title": "Figure 22: Parallel Multi-Threaded Swarm Scaling",
        "description": "Simulation scaling flowchart mapping master orchestrator allocating tasks across parallel worker thread pools.",
        "code": """flowchart LR
    subgraph Master ["Simulation Master"]
        A[Orchestrator Engine]
    end
    subgraph Workers ["Parallel Worker Pool"]
        B[Worker Thread 1]
        C[Worker Thread 2]
        D[Worker Thread 3]
    end
    subgraph Runs ["Monte Carlo Swarms"]
        E[Swarm Batch A]
        F[Swarm Batch B]
        G[Swarm Batch C]
    end

    A -->|Distribute Tasks| B
    A -->|Distribute Tasks| C
    A -->|Distribute Tasks| D

    B -->|Execute| E
    C -->|Execute| F
    D -->|Execute| G"""
    },

    "fig23_agreement_validation": {
        "title": "Figure 23: LLM vs Analyst Label Discrepancy Flowchart",
        "description": "Workflow diagram detailing decision paths for when LLM outputs conflict with human analyst validation labels.",
        "code": """flowchart TD
    Triage[LLM Triage Prediction] --> Validate{Analyst Verification}
    Validate -->|Agree: True Positive| Save1[Save Label as ATTACK]
    Validate -->|Agree: True Negative| Save2[Save Label as BENIGN]
    Validate -->|Disagree: False Positive| Flag1[Flag as FP Noise]
    Validate -->|Disagree: False Negative| Flag2[Flag as Critical Miss]

    Save1 --> Ingest[Postgres Retraining Database]
    Save2 --> Ingest
    Flag1 --> Ingest
    Flag2 --> Ingest"""
    },

    "fig24_adapter_success_flow": {
        "title": "Figure 24: Defensive Mitigation Execution Flow",
        "description": "Flowchart representing response commands mapping to firewall blocking, EDR isolation, or token revocation adapters.",
        "code": """flowchart LR
    Decision[Mitigation Action Plan] --> Router{Orchestration Router}
    Router -->|Firewall Block| FW[pfSense Adapter Stub]
    Router -->|Host Containment| EDR[CrowdStrike Adapter Stub]
    Router -->|Session Revocation| IAM[AuthProvider Adapter Stub]

    FW -->|Response Verify| Loop[Active Verification Loop]
    EDR -->|Response Verify| Loop
    IAM -->|Response Verify| Loop"""
    },

    "fig25_system_steady_states": {
        "title": "Figure 25: System Long-term Healthy vs Threat State Probabilities",
        "description": "Markov state probability chart representing the distribution of stable system states over time.",
        "code": """stateDiagram-v2
    state "Healthy State\\n(Steady State: 65%)" as S1
    state "Alerting State\\n(Steady State: 22%)" as S2
    state "Containment State\\n(Steady State: 11%)" as S3
    state "Compromised State\\n(Steady State: 2%)" as S4

    S1 --> S2 : Attack detected
    S2 --> S3 : Trigger mitigation
    S3 --> S1 : Recovery success
    S2 --> S4 : Mitigation failure
    S4 --> S3 : Emergency response"""
    },

    "fig26_attack_propagation_path": {
        "title": "Figure 26: Most Frequent Exploit Propagation Paths",
        "description": "Chain propagation flow showing statistical paths of host compromises discovered during simulation runs.",
        "code": """flowchart TB
    subgraph Entry ["Threat Initial Entry"]
        A[Public WebServer Exploit]
    end
    subgraph Pivot ["Lateral Movement Hop"]
        B[Admin Jumpbox Compromise]
    end
    subgraph Target ["Critical Assets"]
        C[Production Database]
        D[Backup Storage]
    end

    A -->|Freq: 85%| B
    B -->|Freq: 65%| C
    B -->|Freq: 35%| D"""
    },

    "fig27_owasp_coverage_requirements": {
        "title": "Figure 27: FastAPI OWASP Top 10 Test Coverage Requirements",
        "description": "Requirement diagram mapping test cases to the corresponding OWASP security audit specifications.",
        "code": """requirementDiagram
    requirement security_audit_req {
        id: "1"
        text: "FastAPI endpoints must be hardened against OWASP Top 10 API vulnerabilities"
        risk: medium
        verifymethod: test
    }
    testcase test_broken_auth {
        id: "tc_auth"
        text: "Verify OAuth token expiration and access controls"
    }
    testcase test_injection {
        id: "tc_inj"
        text: "Verify sql and command injection sanitization inputs"
    }
    testcase test_ssrf {
        id: "tc_ssrf"
        text: "Verify webhook hook URL restriction boundaries"
    }
    testcase test_logging_monitoring {
        id: "tc_log"
        text: "Verify security alerts are triggered in Prometheus logs"
    }

    test_broken_auth - satisfies -> security_audit_req
    test_injection - satisfies -> security_audit_req
    test_ssrf - satisfies -> security_audit_req
    test_logging_monitoring - satisfies -> security_audit_req"""
    },

    "fig28_veto_window_sequence": {
        "title": "Figure 28: Auto-Veto Grace Period Event Sequence",
        "description": "Timeline sequence showing message exchanges during the 5-minute automated command veto window.",
        "code": """sequenceDiagram
    autonumber
    participant Triage as Triage LLM
    participant Orch as Response Orchestrator
    participant Analyst as Analyst Console
    participant Agent as EDR Adapter

    Triage->>Orch: Alert triage results severity = 11 (Critical)
    Orch->>Analyst: Raise veto warning action: Isolate Host
    Note over Analyst: 5-minute countdown grace period starts
    Analyst->>Orch: (Optional) Cancel/Veto action
    Note over Orch: If no veto after 300 seconds:
    Orch->>Agent: Commit automatic containment execution
    Agent-->>Orch: Action success confirmation"""
    },

    "fig29_chromadb_embedding_space": {
        "title": "Figure 29: Ingestion & Vector Matching Search Flow",
        "description": "Flow diagram detailing the processing of raw documents into embedding coordinates and matching queries.",
        "code": """flowchart TD
    Doc[Text Ingestion Sources] --> Chunk[Document Chunking Engine]
    Chunk --> Embed[Embedding Generator]
    Embed --> Chroma[(ChromaDB Vector Store)]
    
    Query[Analyst Search Query] --> QEmbed[Embedding Generator]
    QEmbed --> Search{Vector Distance Search}
    Chroma --> Search
    Search -->|Closest Match| Context[Enriched Context Result]"""
    },

    "fig30_incident_lifecycle": {
        "title": "Figure 30: End-to-End Incident Processing Lifecycle",
        "description": "Chronological timeline detailing the 5 core processing phases of a security event from capture to validation.",
        "code": """timeline
    title End-to-End Incident Processing Lifecycle
    Phase 1 : Ingestion : Wazuh agent captures network flow and system alerts
    Phase 2 : Triage : Alert routed to local LLM, ML models categorize binary threat
    Phase 3 : Plan : D3FEND rules map techniques to containment options, scores safety
    Phase 4 : Execution : Automated/Manual adapters apply firewall block or host isolation
    Phase 5 : Verification : Re-simulation validates threat suppression and baseline recovery"""
    }
}

def generate_mermaid_files():
    project_root = Path(__file__).resolve().parent.parent
    mermaid_dir = project_root / "docs" / "mermaid"
    mermaid_dir.mkdir(parents=True, exist_ok=True)
    
    markdown_path = project_root / "docs" / "project_mermaid_diagrams.md"
    
    print(f"Saving individual diagrams in: {mermaid_dir}")
    print(f"Saving consolidated Markdown file in: {markdown_path}")
    
    # 1. Save individual files
    for name, item in DIAGRAMS.items():
        file_path = mermaid_dir / f"{name}.mermaid"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(item["code"])
        print(f"  Saved {name}.mermaid")
        
    # 2. Compile consolidated markdown
    md_content = []
    md_content.append("# Aegis Guard Platform: 30 Project Diagrams (Mermaid)")
    md_content.append("")
    md_content.append("This document gathers 30 unique, project-descriptive diagrams built in Mermaid.js format.")
    md_content.append("Each diagram is specifically structured to follow the golden ratio layout principles and maps to specific modules inside the Aegis Guard platform.")
    md_content.append("")
    md_content.append("---")
    md_content.append("")
    
    for name, item in DIAGRAMS.items():
        md_content.append(f"## {item['title']}")
        md_content.append("")
        md_content.append(f"**Description:** {item['description']}")
        md_content.append("")
        md_content.append("```mermaid")
        md_content.append(item["code"])
        md_content.append("```")
        md_content.append("")
        md_content.append(f"*Individual source file: [docs/mermaid/{name}.mermaid](mermaid/{name}.mermaid)*")
        md_content.append("")
        md_content.append("---")
        md_content.append("")
        
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
        
    print("\nSuccessfully compiled all 30 diagrams into docs/project_mermaid_diagrams.md!")

if __name__ == "__main__":
    generate_mermaid_files()
