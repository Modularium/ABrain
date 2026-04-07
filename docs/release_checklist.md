# Release Checklist

Diese Liste hilft dabei, eine neue Version von ABrain vorzubereiten und zu veröffentlichen.

1. **Tests ausführen**
   ```bash
   ruff check .
   mypy .
   pytest -q
   ```
   Bei fehlenden Abhängigkeiten verwende lokale Wheels oder ein internes Paketmirror.

2. **Integrationen bauen**
   ```bash
   cd integrations/n8n-agentnn && npm install && npx tsc && cd -
   cd integrations/flowise-agentnn && npm install && npx tsc && cd -
   ```
   Die erzeugten Dateien liegen in den jeweiligen `dist/`-Ordnern und müssen vor dem Release hochgeladen werden.

3. **Version aktualisieren**
   - `VERSION` Datei anpassen
   - `CHANGELOG.md` ergänzen

4. **Git-Tag setzen**
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

5. **Artefakte verteilen**
   - JavaScript-Dateien in den Plugin-Manager laden
   - Docker-Images bauen und in die Registry pushen

Diese Schritte stellen sicher, dass ein Release reproduzierbar erstellt wird.
