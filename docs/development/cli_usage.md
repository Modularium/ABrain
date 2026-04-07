# ABrain CLI (`agentnn`)

`agentnn` bietet verschiedene Unterbefehle zum Aufrufen der Services. Der Kommando-Name bleibt als technischer Slug erhalten, obwohl das Projekt fachlich als `ABrain` geführt wird.

## Häufig genutzte Befehle

```bash
agentnn --version
agentnn config show
agentnn model list
agentnn submit --prompt "Beispiel"
```

### Optionen

- `--host` legt den API-Endpunkt fest
- `--token` übergibt das API-Token
- `--session` erlaubt das Weiterführen einer bestehenden Sitzung

Host und Token können dauerhaft über `~/.agentnnrc` konfiguriert werden.
