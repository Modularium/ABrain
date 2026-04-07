# Datenschutzmodell

Dieses Dokument beschreibt die Zugriffsstufen und die Kontextredaktion im ABrain-Framework.

## Zugriffsstufen

| Level | Bedeutung |
|-------|-----------|
| public | frei zugänglich |
| internal | nur intern nutzbar |
| confidential | vertraulich |
| sensitive | stark schützenswert |

Agenten erhalten im Vertrag ein `max_access_level`. Vor jeder Übergabe wird der Kontext mit dem Privacy Filter bereinigt.
