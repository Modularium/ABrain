"""Canonical execution capability surface for ABrain adapters and providers.

This module defines ``ExecutionCapabilities`` — a small, deterministic,
type-safe declaration of what a specific execution adapter can and cannot do.

Design notes
------------
- Static structural facts only, **not** runtime health or availability
  (those belong to ``AgentAvailability`` on the descriptor).
- One ``ExecutionCapabilities`` instance per adapter class, declared as a
  class attribute ``capabilities`` on every ``BaseExecutionAdapter`` subclass.
- Queryable through ``ExecutionAdapterRegistry.get_capabilities_for()``.
- No second registry, no parallel adapter world.

Execution protocols
-------------------
``cli_process``
    Task dispatched by spawning a local subprocess (e.g. ``claude -p …``).
    Requires the CLI binary to be installed on the host.
``http_api``
    Task dispatched via a synchronous HTTP POST to a remote service REST API.
    Requires a reachable service endpoint.
``webhook_json``
    Task dispatched via an HTTP POST to a static webhook URL (workflow engine
    pattern).  Requires a reachable webhook endpoint.
``tool_dispatch``
    Task dispatched through the internal ABrain tool-execution layer without
    any subprocess or network call.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExecutionProtocol = Literal["cli_process", "http_api", "webhook_json", "tool_dispatch"]


class ExecutionCapabilities(BaseModel):
    """Static execution capabilities declared by a specific adapter class.

    All fields are structural facts about the adapter's implementation.
    They do not change at runtime and are safe to cache indefinitely.

    Attributes
    ----------
    execution_protocol:
        How the adapter dispatches work.
    requires_network:
        True if a network call is made during execution.
    requires_local_process:
        True if a local CLI binary or subprocess must be available.
    supports_cost_reporting:
        True if the adapter attempts to extract and populate
        ``ExecutionResult.cost`` from the provider response.
    supports_token_reporting:
        True if the adapter attempts to extract and populate
        ``ExecutionResult.token_count`` from the provider response.
    runtime_constraints:
        Human-readable operational requirements the operator must satisfy
        before the adapter can run (e.g. which metadata keys are required).
    """

    model_config = ConfigDict(extra="forbid")

    execution_protocol: ExecutionProtocol
    requires_network: bool
    requires_local_process: bool
    supports_cost_reporting: bool
    supports_token_reporting: bool
    runtime_constraints: list[str] = Field(default_factory=list)
