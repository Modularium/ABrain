# REVIEW_CHECKLIST

Vor jedem Merge mit Änderungen am AdminBot-Adapter prüfen:

- [ ] Gibt es irgendwo eine freie `action`-Weitergabe?
- [ ] Wird `requested_by` aus User- oder Tool-Daten an AdminBot durchgereicht?
- [ ] Werden nur `run_id` und `correlation_id` aus `ToolExecutionRequest` übernommen?
- [ ] Gibt es neue AdminBot-Tools außerhalb des dokumentierten Scopes?
- [ ] Ist `adminbot_restart_service` weiterhin nicht registriert?
- [ ] Bleiben `error_code`, `message`, `details`, `audit_ref` und `warnings` im Fehlerpfad erhalten?
- [ ] Gibt es neue direkte Legacy-Bypasses an Registry oder Dispatcher vorbei?
