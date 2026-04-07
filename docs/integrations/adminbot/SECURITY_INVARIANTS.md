# SECURITY_INVARIANTS

Diese Bedingungen dürfen durch spätere Änderungen am AdminBot-Adapter nicht verletzt werden:

1. Es gibt keinen generischen AdminBot-Action-Proxy.
2. Es gibt keine freie Action-Weitergabe aus Tool-Inputs oder Modell-Payloads.
3. `requested_by` wird im Adapter hart gesetzt:
   `type = agent`
   `id = agentnn-adminbot-adapter`
4. Aus `ToolExecutionRequest` werden nur `run_id` und `correlation_id` in den AdminBot-Request übernommen.
5. Im erlaubten Default-Scope existieren nur diese read-only Tools:
   `adminbot_get_status`
   `adminbot_get_health`
   `adminbot_get_service_status`
6. `adminbot_restart_service` ist nicht registriert.
7. `adminbot_tail_audit`, `adminbot_validate_policy` und `adminbot_run_gate` sind ebenfalls nicht registriert.
8. Strukturierte AdminBot-Fehler behalten `error_code`, `message`, optionale `details`, optionales `audit_ref` und optionale `warnings`.
9. Lokal gemappt werden nur reine Transport- oder Protokollfehler:
   `ADMINBOT_UNAVAILABLE`
   `ADMINBOT_TIMEOUT`
   `ADMINBOT_PROTOCOL_ERROR`
10. Es gibt keinen Legacy-Bypass um Dispatcher und feste Registry herum.
