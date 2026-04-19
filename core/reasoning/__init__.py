"""Deterministic domain-reasoning layer for ABrain V2.

ABrain V2 interprets external-domain context (LabOS, and eventually
other domain/state systems) into prioritised entities and structured
recommendations, without executing anything itself.  Domain reasoning
is input-driven: the caller supplies a snapshot of the domain state
and the catalogue of actions the target system exposes.  ABrain
reads, prioritises, and proposes; it never invents actions, never
bypasses approval gates, and never assumes side-effects.

Canonical boundary::

    Smolit-AI-Assistant → ABrain (this layer) → LabOS MCP / Tool
    Adapter → LabOS API / DB

Sub-packages
------------
``labos``
    First domain reasoner — normalises a LabOS context snapshot and
    emits the Response Shape V2 for operator-facing reasoning use
    cases (reactor daily overview, incident review, maintenance
    suggestions, schedule runtime review, cross-domain overview).
"""
