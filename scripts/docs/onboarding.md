# Onboarding Guide

Neue Contributor:innen finden hier eine kurze Anleitung für den Einstieg in Agent-NN.

1. **Repository klonen**
   ```bash
   git clone https://github.com/EcoSphereNetwork/Agent-NN.git
   cd Agent-NN
   ```
2. **Setup ausführen**
   ```bash
   ./scripts/setup.sh --preset dev
   ```
3. **Struktur kennenlernen**
   - `scripts/lib/` enthält wiederverwendbare Helper
   - Der canonical runtime stack liegt unter `services/`
   - Historische Bereiche unter `mcp/` sind `legacy (disabled)`
4. **Status prüfen**
   ```bash
   ./scripts/status.sh
   ```
5. **Weitere Informationen**
   - Presets und Konfiguration sind im README beschrieben.
   - Tests laufen mit `./scripts/test.sh`.
