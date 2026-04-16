# Phase R — Domain 5: Governance / Approval / Audit
## Historical Comparison

**Date:** 2026-04-12

---

### Früher (Pre-Phase O)

**Welche Features existierten?**

`core/` (Legacy-Flat-Files):
- `governance.py` — Frühe Governance: AgentContract-Definition, ContractStatus-Enum, simple Enforcement-Checks.
- `governance/legacy_contracts.py` — AgentContract Dataclass: `load(agent_id)`, `save()`, `trust_level_required`, `constraints` (task_history, standing, roles).
- `trust_evaluator.py` — `calculate_trust(agent_id, context) → float`: Berechnet Trust-Score aus Erfolgsrate, Feedback-Score, Token-Efficiency, Reliability. `eligible_for_role(agent_id, target_role) → bool`. `update_trust_usage()`.
- `trust_network.py` — Persistentes Trust-Netzwerk: `TrustEdge` (from→to, weight, relation, timestamp), `TrustGraph`. Speichert als JSONL.
- `trust_circle.py` — TrustCircle: Gruppe von Agenten mit geteiltem Trust-Level. Ermöglicht Delegation innerhalb des Kreises.
- `reputation.py` — `ReputationScore`: `success_rate`, `peer_rating`, `task_count`, `aggregate_score()`. Persistiert als JSON.
- `roles.py` — `AgentRole` Enum, `resolve_roles(agent_id) → List[str]`.
- `role_capabilities.py` — `RoleCapabilityMap`: Welche Capabilities hat welche Role? `has_capability(agent_id, cap)`.
- `access_control.py` — Token-basierte Access Control: `AccessToken`, `AccessLevel` (NONE/READ/WRITE/ADMIN). `validate_token()`.
- `delegation.py` — Formale Delegation: `DelegationGrant` (delegator, delegate, role, scope, expires_at). Persistiert als JSONL.
- `voting.py` — Voting/Consensus: `VoteRecord`, `tally_votes()`, Mehrheitsentscheid.
- `self_reflection.py` — Agent Self-Reflection: `SelfReflectionResult`, `reflect(agent_id, task, result)`. Speichert Reflexionen.
- `crypto.py` — ECDSA-Signing: `sign_message()`, `verify_signature()`, Agenten-Identitäten mit Schlüsseln.

`security/input_filter.py` — Input-Sanitization: Shell-Injection-Detection, XSS-Filter, Size-Limits.

**Wie war die Architektur?**
- Governance war *deklarativ*: AgentContracts wurden gespeichert, aber nicht enforced beim Task-Dispatch.
- Trust war ein *Post-Hoc-Score*, kein Pre-Execution-Gate.
- Kein formales Approval-System für menschliche Überprüfung.
- Kein Audit-Trail mit strukturierten Spans/Traces.
- Die Konzepte waren *zahlreich aber lose*: 10+ verschiedene Governance-Konzepte ohne klare Hierarchie.

**Welche Probleme gab es?**
- Governance war nie in den Request-Pfad integriert: Ein Agent konnte eine Aufgabe ausführen ohne je seinen Contract zu prüfen.
- Trust-Score war gut konzipiert aber nicht mit Routing verbunden: Routing ignorierte den Trust-Score.
- Keine HITL-Approval für kritische Aktionen.
- Kein strukturierter Audit-Trail: Logs in Dateien, kein Query-fähiger Store.
- `crypto.py` (ECDSA) hatte keine Integration in andere Teile: Identitäten wurden signiert aber nie verifiziert im Request-Pfad.
- Zu viele parallele Governance-Konzepte → keine Priorität klar.

---

### Heute (Post-Phase O)

**Was ist kanonisch vorhanden?**

`core/governance/`:
- `policy_models.py` — `PolicyRule` (id, condition_fn, action, severity), `GovernanceDecision`, `GovernanceViolation`.
- `policy_registry.py` — `PolicyRegistry`: Registriert und lädt Policy-Rules.
- `policy_engine.py` — `PolicyEngine`: Evaluiert Tasks gegen alle aktiven Policies. Gibt `GovernanceDecision` zurück.
- `enforcement.py` — `enforce_policy()`: Blockiert Task-Ausführung bei Policy-Verletzung.

`core/approval/`:
- `models.py` — `ApprovalRequest`, `ApprovalStatus`, `ApprovalAction`.
- `policy.py` — `ApprovalPolicy`: Definiert welche Tasks menschliche Überprüfung benötigen.
- `store.py` — `ApprovalStore` (JSON-persistent): Speichert ausstehende/entschiedene Approvals.

`core/audit/`:
- `trace_models.py` — `TraceSpan`, `TraceRecord`, `ExplainabilityRecord`.
- `trace_store.py` — `TraceStore` (SQLite): Persistiert alle Traces und Spans.
- `context.py` — `TraceContext`: Span-Propagation.
- `exporters/` — Export-Adapter (base).

**Wie ist es strukturiert?**
- Policy-Enforcement ist *strukturell* im Request-Pfad: Kein Task kann ausgeführt werden ohne Policy-Check.
- Approval ist *persistiert* (JSON) und übersteht Process-Restarts.
- Audit/Trace ist *vollständig* (SQLite): Jeder Task, jedes Approval, jede Policy-Entscheidung wird aufgezeichnet.
- Klarer Pfad: `run_task → enforce_policy → check_approval → execute → trace`.

**Was wurde bewusst entfernt?**
- Trust-Score-basiertes Routing (durch Policy-Engine ersetzt).
- Agent-Coalitions (durch Orchestration/Plan ersetzt).
- Delegation-Grants (Scope zu komplex für aktuellen Stand).
- ECDSA Crypto (kein echter Anwendungsfall mehr).
- Voting/Consensus (durch Policy-Engine und HITL ersetzt).
- Self-Reflection (durch Explainability in Audit-Layer ersetzt).

---

### Bewertung

**Was war früher schlechter?**
- Governance war deklarativ, nicht enforced.
- Zu viele parallele Konzepte ohne Priorisierung.
- Kein Audit-Trail in Query-fähigem Format.
- Trust-Score hatte keinen Effekt auf das Routing.

**Was ist heute besser?**
- Policy-Enforcement ist strukturell im Pfad.
- HITL-Approval ist persistiert und robust.
- SQLite-Trace-Store ist query-fähig.
- Klarer Pfad: kein Task kommt durch ohne Policy + optional Approval.

**Wo gab es frühere Stärken?**
- `trust_evaluator.py` hatte eine *mathematisch elegante* Trust-Formel: (Erfolgsrate + Feedback + Token-Efficiency + Reliability) / 4. Das ist ein konkreter, messbarer Trust-Wert pro Agent, der auf historischen Daten basiert. Heute gibt es keinen vergleichbaren aggregierten Agent-Trust-Score.
- `delegation.py` ermöglichte *formale, scoped Delegation* mit Ablaufzeiten (`scope: task/mission/team/permanent`, `expires_at`). Das ist ein reales Feature in Multi-Agenten-Systemen.
- `reputation.py` mit `peer_rating` — Agenten konnten von anderen Agenten bewertet werden. Das fehlt komplett heute.
- `trust_network.py` als Graph — Trust-Beziehungen zwischen Agenten als gerichteter Graph. Für Systeme mit vielen Agenten ein wichtiges Konzept.
- `voting.py` — Mehrheitsentscheid für Konsens-Entscheidungen. Für kritische Aktionen ein sinnvoller Mechanismus.
- `self_reflection.py` — Agenten reflektieren über ihre eigenen Ergebnisse. Das ist ein Kernaspekt moderner AI-Systeme (RLHF, Self-Critique).

---

### Gap-Analyse

**Was fehlt heute?**
- Kein Agent-Trust-Score basierend auf historischer Performance.
- Kein Peer-Rating zwischen Agenten.
- Keine formale scoped Delegation.
- Kein Voting/Konsens-Mechanismus für kritische Policy-Entscheidungen.
- Self-Reflection der Agenten fehlt (obwohl Explainability im Trace-Layer existiert).

**Welche Ideen sind verloren gegangen?**
- Agent-Identitäten mit kryptographischen Schlüsseln (ECDSA). Für produktive Multi-Tenant-Systeme relevant.
- Trust-basiertes Routing: High-Trust-Agenten könnten ohne Approval ausführen, Low-Trust-Agenten immer Approval benötigen.

---

### Relevanz heute

| Konzept | Relevanz |
|---|---|
| AgentContract (deklarativ, nicht enforced) | A — bewusst verworfen |
| Trust-Score basiertes Routing | D — **kritisch wertvoll**: Trust → kann ApprovalPolicy steuern |
| Peer-Rating | B — interessant, aber nicht priorisiert |
| Delegation-Grants (scoped) | C — wertvoll für Multi-Agenten, Neubau nötig |
| Voting/Konsens | B — interessant, aber heute durch HITL abgedeckt |
| Self-Reflection der Agenten | C — wertvoll, als Extension des Explainability-Layers |
| ECDSA Crypto | B — interessant für Multi-Tenant, heute kein Anwendungsfall |
| Trust-Network als Graph | C — interessant für zukünftige Systeme |
