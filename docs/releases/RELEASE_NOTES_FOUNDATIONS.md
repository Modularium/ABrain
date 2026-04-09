# ABrain Foundations Release Notes v1.1.0

## Produktzusammenfassung

Mit `v1.1.0` liegt erstmals ein zusammenhängender ABrain-Foundations-Stack auf dem aktuellen Architekturpfad vor. Der Release bündelt kanonisches Agentenmodell, Decision Layer, Execution Layer, Learning-System, den verified AdminBot-v2-Adapter und die dünnen Interop-/Interface-Schichten.

## Wichtigste Architekturbausteine

- kanonisches `AgentDescriptor`-Modell mit Capabilities und Registry
- Flowise-Interop als Import-/Export-Layer, nicht als interne Wahrheit
- deterministischer `Planner` und `CandidateFilter`
- verpflichtendes `NeuralPolicyModel` für Ranking sicherer Kandidaten
- `ExecutionEngine` mit statischer Adapter-Registry
- Feedback- und Learning-Pfad mit Trainingsdaten, Reward-Modell und Trainer

## Sicherheitsmodell

- Sicherheitsrelevante Grenzen bleiben deterministisch.
- `CandidateFilter` und Policy-Checks laufen vor dem NN.
- Das NN beeinflusst nur Ranking, nicht Tool-Freigaben oder Zugriff.
- AdminBot bleibt read-only und nur über den gehärteten Core angebunden.
- MCP und Flowise bleiben Interface-/Interop-Layer, nicht Kernlogik.

## Was jetzt funktioniert

- kanonische Agentenmodellierung und lokale Registry-Nutzung
- Flowise-kompatibler Import/Export für die definierte Minimalmenge
- Routing über Planner -> CandidateFilter -> NeuralPolicyModel
- Ausführung über statische Adapter und `ExecutionEngine`
- `run_task(...)` mit Routing, Execution, Feedback und best-effort Learning
- Online-Erzeugung von Trainingssamples und periodisches Inline-Training

## Was bewusst noch nicht Teil des Releases ist

- Multi-Agent-Orchestrierung
- breite MCP-Tool-Expansion
- Hintergrund-Training oder fortgeschrittene Lernstrategien
- produktionsreife native Spezialadapter jenseits des aktuellen Referenzpfads
- aggressive Umbenennung technischer Paket- und Deployment-Slugs

## Upgrade- und Migrationshinweise

- Sichtbare Produktidentität ist jetzt `ABrain`.
- Technische Slugs wie `agentnn` oder `agent-nn` bleiben vorerst bestehen.
- Für sicherheitsrelevante Integrationen bleibt `services/core.py -> core/*` der Referenzpfad.
- Historische MCP-, Supervisor- und NNManager-Pfade sind nicht mehr kanonische Wahrheit.

## Bekannte Grenzen

- automatische Modell- und Dataset-Persistenz ist noch explizit statt voll verdrahtet
- der Learning-Pfad trainiert klein und inline, nicht als separater Worker
- ältere Dokumente und Betriebsartefakte mit `Agent-NN`-Slugs können historisch weiter vorhanden sein
