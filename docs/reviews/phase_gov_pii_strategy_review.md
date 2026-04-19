# §6.4 Data Governance — PII-Strategie review

**Branch:** `codex/phase-gov-pii-strategy`
**Date:** 2026-04-19
**Scope:** read-only PII detection surface for `core/audit/` —
`PiiPolicy` + `PiiDetector` primitive plus a composition helper
`annotate_retention_candidates` that scans the records referenced by a
`RetentionReport` and produces per-candidate findings. No writes, no
second audit stack.

Closes the §6.4 "PII-Strategie" line item. Composes cleanly with the
retention scanner + pruner shipped in the prior two turns and with the
Phase 5 dataset builder (which also speaks in terms of text fields).

---

## 1. Roadmap position

`docs/ROADMAP_consolidated.md` §6.4 before this turn:

- [x] Datenschema für Training und Auswertung
- [ ] Provenienz und Lizenzstatus je Datenquelle
- [ ] **PII-Strategie** ← this turn
- [x] Retention- und Löschkonzept (Scanner + Pruner)
- [ ] reproduzierbare Datensplits

The previous turn's recommendation was verbatim:

> "Recommendation for the next turn: §6.4 *'PII-Strategie'* — a policy +
> detection surface that tags retention candidates (and future
> training-data records) with PII classifications."

That is exactly this turn.

### Idempotency check

Before building:

- `grep -rn 'PII\|pii_\|PiiClassif\|pii_scan'` found only the
  source-level `pii_risk: bool` flag on `core/retrieval/models.py` (a
  Phase 3 ingestion-time signal — orthogonal and intentionally narrow);
- no existing detector, classifier, or scan module under `core/`;
- no parallel branch tracks this scope;
- the retention scanner + pruner are already on main and expose the
  exact `RetentionReport` shape this helper composes with.

Nothing was double-built. The new module is additive — zero existing
call sites behave differently.

---

## 2. Design

### Detector is policy-driven, stateless, and stdlib-only

`PiiDetector(policy=PiiPolicy(...))` compiles the active regexes once at
construction and exposes `scan_text(str)` / `scan_fields(dict)`. It
holds no per-call state. Pydantic + `re` only — no new dependencies.

### No raw PII ever leaves the detector

`PiiMatch` carries `category`, `span_start`, `span_end`, and a fixed
`placeholder` string (e.g. `"[email]"`). It does **not** carry the
matched substring. This is the central safety property of the module:
serialising a `PiiScanResult` to disk, a log, or an audit surface
cannot re-leak the PII it just detected. A scanner that stored the
original bytes in its result would be a second way for PII to escape
the canonical store — which defeats the purpose.

### Policy is orthogonal to retention

`PiiPolicy` does not speak about retention windows, age, or deletion.
`RetentionPolicy` does not speak about content classification. A
caller composes them via `annotate_retention_candidates(detector,
report, trace_store, approval_store)`, which:

- takes a `RetentionReport` as the source of truth for "which records";
- asks the detector for "which fields carry PII";
- returns a **separate** `PiiRetentionAnnotation` surface.

Two reasons this separation matters:

- retention and PII evolve on different cadences — PII categories
  expand over time; retention windows change per compliance regime;
- a future Phase 5 dataset builder can reuse `PiiDetector.scan_fields`
  against training records without ever materialising a
  `RetentionReport`.

### Conservative built-in categories

`DEFAULT_PII_CATEGORIES = ("email", "ipv4", "credit_card", "iban",
"api_key")`. `ipv6` and `phone` patterns are available but not
default — their regexes are inherently prone to false positives on
non-PII numeric content. Callers can opt in.

`PiiPattern` allows custom regexes with a caller-chosen category name;
custom categories cannot collide with built-in names (validated at
construction time), so a custom pattern cannot silently shadow or
override a built-in.

### Retention annotation is read-only and tolerant of concurrent deletion

`annotate_retention_candidates` never mutates either store and never
rewrites the input `RetentionReport`. If a candidate record has been
deleted between `scan` and `annotate` (e.g. the pruner already ran),
the helper emits an empty-result annotation for that candidate rather
than raising. This matches the retention pruner's concurrent-deletion
behaviour from the prior turn — the whole governance surface is
idempotent under concurrent mutation.

### No audit-log write from the detector

Same contract as the retention pruner: the detector and the annotation
helper are pure primitives. The caller (a governance surface, a
scheduled job, a CLI) owns the operator audit trail. Adding a second
audit writer here would create a parallel audit stack — which
explicitly violates invariant B.5 (no second trace / approval / audit
stack).

---

## 3. Public API

```python
from core.audit import (
    PiiPolicy,
    PiiDetector,
    PiiPattern,
    PiiScanResult,
    PiiRetentionAnnotation,
    annotate_retention_candidates,
    RetentionPolicy,
    RetentionScanner,
)

# 1. Policy — conservative defaults, or opt-in categories / custom rules.
policy = PiiPolicy(
    enabled_categories=["email", "ipv4", "api_key"],
    custom_patterns=[
        PiiPattern(category="employee_id", pattern=r"\bEMP-\d{5}\b"),
    ],
)
detector = PiiDetector(policy=policy)

# 2a. Pure text classification.
result = detector.scan_fields({
    "user_message": "contact bob@example.com",
    "system_note":  "no pii here",
})

# 2b. Compose with retention — annotate candidates from a RetentionReport.
scanner = RetentionScanner(
    trace_store=trace_store,
    approval_store=approval_store,
    policy=RetentionPolicy(trace_retention_days=90, approval_retention_days=365),
)
report = scanner.scan()

annotation: PiiRetentionAnnotation = annotate_retention_candidates(
    detector=detector,
    report=report,
    trace_store=trace_store,
    approval_store=approval_store,
)
```

---

## 4. Invariants preserved

| Invariant | Status |
|---|---|
| No parallel trace / approval stack | ✅ — scanner reads from canonical stores only |
| No second audit stack | ✅ — detector writes no audit entries of its own |
| No business logic in CLI / UI / schemas | ✅ — pure classification primitive |
| No hidden reactivation of legacy | ✅ — greenfield addition, `core/retrieval` `pii_risk` flag untouched |
| No second retention surface | ✅ — `PiiPolicy` is orthogonal; composition is a helper, not a re-decision |
| Read-only composition with `RetentionReport` | ✅ — stores are never mutated |
| No raw-PII leakage from the detector | ✅ — `PiiMatch.placeholder` carries only a fixed mask |
| Additive only | ✅ — one new module + exports + tests + doc |
| No new dependencies | ✅ — stdlib `re` + pydantic |

---

## 5. Artifacts

| File | Purpose |
|---|---|
| `core/audit/pii.py` | `PiiPolicy`, `PiiPattern`, `PiiMatch`, `PiiFinding`, `PiiScanResult`, `PiiDetector`, `PiiCandidateAnnotation`, `PiiRetentionAnnotation`, `annotate_retention_candidates`, `DEFAULT_PII_CATEGORIES` |
| `core/audit/__init__.py` | re-exports the 10 new PII symbols |
| `tests/audit/test_pii.py` | 23 unit tests |
| `docs/reviews/phase_gov_pii_strategy_review.md` | this doc |

---

## 6. Test coverage

23 tests, all green:

- **TestPolicy** (5) — default policy selects the conservative built-in
  set; enabled categories are deduped; custom pattern cannot collide
  with a built-in name; invalid regex fails at construction;
  `extra="forbid"` on `PiiPolicy`.
- **TestDetectorBuiltins** (6) — email / ipv4 / iban / api_key detected
  with fixed placeholder (no raw bytes); matches sorted by span;
  empty-text shortcut.
- **TestDetectorCustom** (3) — disabled category is not detected;
  custom regex detected and carries caller's category name;
  `scan_fields` counts scanned fields and aggregates per-category
  totals.
- **TestRetentionAnnotation** (4) — trace + approval candidates each
  produce per-kind findings; stores are untouched after annotation and
  re-scan is deterministic; concurrent candidate deletion yields an
  empty-result entry rather than an error; empty report yields empty
  annotation.
- **TestSchemaHardening** (5) — `extra="forbid"` enforced on every new
  pydantic surface (`PiiMatch`, `PiiFinding`, `PiiScanResult`,
  `PiiCandidateAnnotation`, `PiiRetentionAnnotation`).

### Suites

- Mandatory + `tests/audit`: **1202 passed, 1 skipped** (+23 over the
  1179 baseline from the prior turn).
- Full (`tests/` with `test_*.py`): **1615 passed, 1 skipped** (+23
  over the 1592 baseline from the prior turn).

---

## 7. Merge-readiness

| Check | Result |
|---|---|
| Scope correct (policy + detector + read-only retention composition) | ✅ |
| No parallel structure introduced | ✅ |
| Canonical stores read-only | ✅ |
| No new shadow source-of-truth | ✅ |
| Detector never leaks raw PII | ✅ |
| Mandatory suite green | ✅ |
| Full suite green (+23 new) | ✅ |
| Documentation consistent | ✅ |
| **Merge-ready** | ✅ |

---

## 8. Next step

§6.4 Data Governance after this turn:

- [x] Datenschema für Training und Auswertung
- [ ] Provenienz und Lizenzstatus je Datenquelle
- [x] PII-Strategie — **closed this turn**
- [x] Retention- und Löschkonzept
- [ ] reproduzierbare Datensplits — deferred to Phase 5 data pipeline

**Recommendation for the next turn:** §6.4 *"Provenienz und Lizenzstatus
je Datenquelle"* — a metadata surface on ingestion sources that
formalises the partial provenance tracking already in `core/retrieval`
(the existing `DataSource` descriptor in `core/retrieval/models.py`
carries `license`, `pii_risk`, `retention_days`; this would elevate it
to a reviewable governance report, analogous to what the retention
scanner does for deletion candidates).

Alternative of comparable weight: skip §6.4 and start Phase 5's
reproducible-splits surface when the dataset builder is next touched;
this moves the roadmap forward rather than deeper into governance.

Phase 7 stays deferred until a real-traffic `promote` verdict from
`BrainOperationsReporter` is on record.
