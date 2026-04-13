# SECURITY_INVARIANTS

Diese Bedingungen dürfen durch spätere Änderungen am AdminBot-Adapter nicht verletzt werden:

1. Es gibt keinen generischen AdminBot-Action-Proxy.
2. Es gibt keine freie Action-Weitergabe aus Tool-Inputs oder Modell-Payloads.
3. `requested_by` wird im Adapter hart gesetzt:
   `type = agent`
   `id = abrain-adminbot-adapter`
4. Aus `ToolExecutionRequest` werden nur `run_id` und `correlation_id` in den AdminBot-Request übernommen.
5. Im erlaubten Default-Scope existieren nur diese read-only Tools:
   `adminbot_system_status`
   `adminbot_system_health`
   `adminbot_service_status`
6. `adminbot_service_restart` ist nicht registriert.
7. `adminbot_resource_snapshot`, `adminbot_journal_query` und `adminbot_process_snapshot` sind in dieser Phase ebenfalls nicht registriert.
8. Strukturierte AdminBot-Fehler behalten `error_code`, `message`, optionale `details`, optionales `audit_ref` und optionale `warnings`.
9. Lokal gemappt werden nur reine Transport- oder Protokollfehler:
   `ADMINBOT_UNAVAILABLE`
   `ADMINBOT_TIMEOUT`
   `ADMINBOT_PROTOCOL_ERROR`
10. Es gibt keinen Legacy-Bypass um Dispatcher und feste Registry herum.
