# Post-Consolidation Next Steps

## Bewusst offen gelassene Alt-Funde

- lokale `.env`-Dateien aus dem Backup
- lokale Logs, Datenbanken und Caches aus dem Backup
- ältere Codeversionen der jetzt gehärteten Einstiegspfade
- leere Alt-Verzeichnisse ohne Quellwert

Diese Inhalte wurden absichtlich nicht übernommen, weil sie keinen reviewbaren Source-Gewinn liefern oder den sicheren Zielstand verwässern würden.

## Nächste separate Schritte

1. externe Repo-/Slug-Umbenennung außerhalb des Repos abschließen
2. README- und Setup-Dokumentation weiter verfeinern
3. CI über die bestehenden Security-Gates hinaus schrittweise ausbauen
4. weitere frühere Review-Punkte systematisch auf den gehärteten Core abbilden

## Nach der Konsolidierung weiter relevante Punkte

- noch offene technische Slugs wie `agentnn`, `agent-nn` und Repo-URLs separat migrieren
- Doku-Lücken in README, Setup-Flow und Entwicklerdokumentation
- weitere Testabdeckung für Service-Helfer und Legacy-Kompatibilität
- CI-Ausbau über die AdminBot-Sicherheitsgates hinaus
- systematische Bewertung älterer Modell-, Knowledge- und Management-Bereiche gegen die neue Core-Schicht
- weitere Multi-Agent-Weiterentwicklung nur über die gehärtete Dispatcher-/Registry-Struktur
