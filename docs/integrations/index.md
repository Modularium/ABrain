# Integrations

Dieses Kapitel beschreibt, wie ABrain mit externen Tools gekoppelt werden kann. Neben der Smolitux-UI stehen Erweiterungen für n8n und FlowiseAI bereit. Beide Systeme können ABrain aufrufen und umgekehrt von ABrain aus gesteuert werden. Historische Plugin-Pfade unter `plugins/` sind `historical / legacy (not active runtime path)` und kein `canonical path` mehr.

Für die Beispielintegration ist es erforderlich, die TypeScript-Dateien zunächst mit `npm install` und `npx tsc` zu kompilieren. Die erzeugten JavaScript-Dateien werden anschließend vom jeweiligen PluginManager geladen.

Schnelleinstiege findest du in den jeweiligen Kapiteln [n8n](n8n.md#quick-start) und [FlowiseAI](flowise.md#quickstart). Eine detaillierte Beschreibung der mitgelieferten Flowise-Workflows befindet sich unter [OpenHands Workflows](openhands_workflows.md).
Weitere Beispiele für Flowise-Komponenten sind in [flowise_nodes.md](../flowise_nodes.md) aufgelistet.

Eine ausführliche Roadmap zur beidseitigen Integration findet sich in [full_integration_plan.md](full_integration_plan.md).
