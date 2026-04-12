# Phase R2 — Provider / LLM / Backend Abstraction Assessment

## 1. Was war früher an der Provider-Abstraktion gut?

### config/llm_config.py + config/__init__.py
```python
LLM_BACKEND = os.getenv("LLM_BACKEND", "lmstudio")  # "openai" | "lmstudio"
OPENAI_CONFIG = {"api_key": ..., "model": ..., "temperature": ...}
LMSTUDIO_CONFIG = {"base_url": "http://localhost:1234/v1", "model": ...}
```
**Stärken:**
- Einfaches Umgebungsvariablen-basiertes Backend-Switching
- Klare Trennung zwischen Cloud (OpenAI) und Lokal (LM Studio)
- Beide Backends über gemeinsame Langchain-Abstraktion verwendbar

### SpecializedLLMManager
- Domain-spezifische Modell-Konfigurationen (JSON-Dateien pro Domain)
- `get_best_model(domain, task_description)` — performance-basierte Modell-Auswahl
- Training-Status-Tracking pro Modell (`initialized`, `training`, `ready`)
- `update_model_metrics()` + `get_model_stats()` — Observability

**Stärken:**
- Idee: unterschiedliche Modelle für unterschiedliche Domains verwenden
- Explizite Trennung zwischen Modell-Konfiguration und Modell-Verwendung

**Schwächen:**
- Kein gemeinsames Interface/Protokoll für alle Modelle
- Training-Status war string-basiert, kein typsicheres State-Machine
- `get_best_model()` wählte nur basierend auf In-Memory-Metriken, kein Persistenz

### ModelManager (model_manager.py)
```python
class ModelSource:
    LOCAL = "local"
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"
```
**Stärken:**
- Drei-Klassen-Abstraktion (Local/HuggingFace/OpenAI) war konzeptionell klar
- Einheitliche `load_model(name, type, source, config)` API
- Versions-Registry

**Schwächen:**
- `_load_openai_model()` hatte Typo (`aretrive` statt `aretrieve`) — war nie getestet
- Kein echtes Common-Interface (duck-typing, kein Protocol/ABC)
- Models wurden als Dict mit allem möglichen (model object, tokenizer, metadata) gespeichert

---

## 2. Was fehlt heute?

### Heute in adapters/
```
adapters/adminbot/     → AdminBot v2 Read-only
adapters/flowise/      → Flowise Workflow-Adapter
adapters/__init__.py
```

### Heute in AgentDescriptor
```python
class AgentSourceType(StrEnum):
    OPENHANDS = "openhands"
    CODEX = "codex"
    CLAUDE = "claude"
    FLOWISE = "flowise"
    N8N = "n8n"
    INTERNAL = "internal"
    CUSTOM = "custom"
```

**Was ist heute gut:**
- AgentSourceType als First-Class-Enum im Routing
- Adapter-Pattern für externe Tools (OpenHands, Codex, Claude, Flowise)
- Keine schweren ML-Dependencies im Kern

**Was fehlt:**
- Kein Mechanismus für **LLM-Provider-Auswahl pro Task** (manche Tasks billiger mit GPT-3.5, andere brauchen GPT-4)
- Kein **Lokales/Cloud-Hybrid-Routing** (Task-Sensitivity bestimmt ob lokal oder Cloud)
- Keine **Provider-Health-Checks** (ist Provider X gerade verfügbar? Was ist die aktuelle Latenz?)
- Kein **Cost-Ceiling pro Task** (max_api_cost als Policy-Constraint)
- Keine **Fallback-Chain** (wenn OpenAI nicht verfügbar → lokales Modell)

---

## 3. Was war gut und könnte architekturkonform neu eingebaut werden?

### A. Provider-Health-Tracking im AgentDescriptor
**Alt:** `SpecializedLLMManager` mit In-Memory-Status
**Neu (sauber):** `AgentDescriptor.availability` + `AgentDescriptor.metadata["last_health_check"]`

AgentDescriptor hat bereits `availability: AgentAvailability (ONLINE/OFFLINE/DEGRADED)`. Ein leichter Provider-Health-Checker der periodisch Availability aktualisiert würde das komplettieren.

**Bewertung:** Kategorie C — klein, sauber, hochwertig.

### B. Cost-Ceiling als Policy-Rule
**Alt:** Kein Äquivalent
**Neu (sauber):** `PolicyRule` mit `max_cost_per_execution` → Effect: "deny" wenn AgentDescriptor.cost_profile > ceiling

`core/governance/` bietet genau den richtigen Ort: eine Policy-Rule die `AgentCostProfile` gegen einen konfigurierten Ceiling prüft.

**Bewertung:** Kategorie C — direkt in PolicyEngine integrierbar.

### C. Lokales/Cloud-Hybrid-Routing
**Alt:** `LLM_BACKEND` Environment-Variable (global)
**Neu (sauber):** `TaskIntent.execution_hints["prefer_local"]` + Policy-Rule die das durchsetzt

Heute hat `execution_hints` bereits dieses Konzept implizit. Ein Policy-Rule "für sensitive Tasks → require local" wäre klein und wertvoll.

**Bewertung:** Kategorie C — über Policy + execution_hints realisierbar.

### D. Fallback-Chain für Provider-Ausfälle
**Alt:** Kein Äquivalent
**Neu (sauber):** Im Orchestrator: wenn `ExecutionResult.success == False` und `reason == "provider_unavailable"` → Route neu mit `exclude=[failed_agent_id]`

Das Orchestration-Layer hat die Struktur dafür. Retry-Logik mit Exclusion-Set wäre eine sinnvolle Erweiterung.

**Bewertung:** Kategorie C — Orchestration-Erweiterung.

---

## 4. Was würde heute zu viel Komplexität zurückbringen?

### A. SpecializedLLMManager als separater Service
- Würde parallele Modell-Auswahl außerhalb der Routing-Engine erzeugen
- **Nicht zurückholen**

### B. ModelManager mit HuggingFace-Modell-Loading
- Bringt `transformers`, `torch` in den Core
- ABrain-Agenten sind externe Tools (OpenHands, Codex, etc.) — kein lokaler Modell-Load im Core
- **Nicht zurückholen**

### C. YAML/JSON-Config-basierte Provider-Modelle (wie domain_knowledge_manager)
- War komplex ohne strukturierte Validierung
- Heute besser über AgentDescriptor.metadata + YAML-Seed-Daten für AgentRegistry
- Das YAML-Seed-Konzept ist schon implizit da — nicht nochmal als Manager

### D. lokaler LM-Studio Embedding-Server im Core
- War für Semantic-Matching, könnte als Feature interessant sein
- Aber: bringt Runtime-Dependency auf externen HTTP-Service
- Besser: lightweight BM25/TF-IDF ohne HTTP-Dependency

---

## 5. Zusammenfassung

| Aspekt | Alt | Heute | Lücke | Empfehlung |
|---|---|---|---|---|
| Backend-Switching (env var) | ✅ | ❌ (design: adapters) | Ja | C: execution_hints |
| Provider-Health-Tracking | ✅ (In-Memory) | ✅ (AgentDescriptor.availability) | Teilweise | C: Health-Updater |
| Cost-Ceiling | ❌ | ❌ | Ja | C: Policy-Rule |
| Domain-spez. Modell-Auswahl | ✅ | ❌ | Ja | C: als Routing-Hint |
| Fallback-Chain | ❌ | ❌ | Ja | C: Orchestration-Retry |
| Local/Cloud Hybrid | ✅ (env) | ❌ (explizit) | Ja | C: execution_hints + Policy |
| Modell-Versions-Registry | ✅ (PyTorch) | ✅ (JSON, lightweight) | Nein | — |
| HF/OpenAI Modell-Loading | ✅ | ❌ (design) | Nein (bewusst) | A: nicht zurück |
