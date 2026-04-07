---
slug: /BenutzerHandbuch
---

# Agent-NN: Benutzerhandbuch

> Hinweis: Historischer Produkt- und UX-Stand. Diese Langform-Doku bleibt zur Referenz erhalten, ist aber nicht die maßgebliche Beschreibung des heutigen gehärteten ABrain-Core- und AdminBot-Pfads.

## Inhaltsverzeichnis

1. [Einführung](#einführung)
2. [Systemüberblick](#systemüberblick)
3. [Erste Schritte](#erste-schritte)
4. [Die Benutzeroberfläche](#die-benutzeroberfläche)
5. [Mit Agenten interagieren](#mit-agenten-interagieren)
6. [Domänenspezifische Agenten](#domänenspezifische-agenten)
7. [Wissensmanagement](#wissensmanagement)
8. [Erweiterte Funktionen](#erweiterte-funktionen)
9. [Fehlerbehebung](#fehlerbehebung)
10. [Häufig gestellte Fragen](#häufig-gestellte-fragen)
11. [Kontakt und Support](#kontakt-und-support)

## Einführung

Willkommen bei Agent-NN, Ihrem fortschrittlichen Multi-Agent-System für domänenspezifische Assistenz und Aufgabenautomatisierung. Agent-NN kombiniert die Leistungsfähigkeit von modernen Sprachmodellen mit spezialisierten Wissensbasen, um maßgeschneiderte Hilfe in verschiedenen Fachbereichen anzubieten.

Diese Dokumentation führt Sie durch alle Funktionen und Möglichkeiten des Systems und zeigt Ihnen, wie Sie von der Leistungsfähigkeit spezialisierter KI-Agenten profitieren können.

### Was ist Agent-NN?

Agent-NN ist ein intelligentes Assistenzsystem, das unterschiedliche spezialisierte Agenten für verschiedene Wissensbereiche und Aufgabentypen koordiniert. Anders als herkömmliche KI-Assistenten, die als Generalisten arbeiten, bietet Agent-NN Zugang zu maßgeschneiderten Experten für Bereiche wie Finanzen, Technologie, Marketing und mehr.

### Hauptmerkmale

- **Domänenspezifische Expertise**: Spezialisierte Agenten für verschiedene Fachbereiche
- **Kollaborative Intelligenz**: Agenten, die zusammenarbeiten, um komplexe Aufgaben zu lösen
- **Kontinuierliche Verbesserung**: Agenten, die aus Interaktionen lernen und sich verbessern
- **Wissensbasierte Antworten**: Präzise Antworten basierend auf verifiziertem Fachwissen
- **Web-Integration**: Automatische Datenerfassung und -aktualisierung aus dem Web

## Systemüberblick

Agent-NN besteht aus mehreren Hauptkomponenten, die zusammenarbeiten, um Ihnen ein leistungsstarkes Assistenzsystem zu bieten.

![Systemarchitektur](Systemarchitektur.svg)

### Hauptkomponenten

1. **Chatbot-Interface**: Ihr Haupteinstiegspunkt für die Interaktion mit dem System
2. **Supervisor-Agent**: Analysiert Anfragen und leitet sie an die passenden Spezialisten weiter
3. **Fach-Agenten**: Spezialisierte Experten für verschiedene Wissensdomänen
4. **Wissensbasen**: Domänenspezifische Informationsquellen für fundierte Antworten
5. **Web-Crawler**: System für die automatische Aktualisierung von Informationen

### Agententypen

Agent-NN bietet verschiedene Arten von Agenten, jeder mit einzigartigen Fähigkeiten:

![Agententypen](Agententypen.svg)

- **Finanz-Agent**: Experte für Finanzanalyse, Investitionen und Finanzplanung
- **Tech-Agent**: Spezialist für Softwareentwicklung, Systemarchitektur und technische Problemlösung
- **Marketing-Agent**: Experte für Marketingstrategien, digitales Marketing und Markenentwicklung
- **Web-Agent**: Spezialist für die Beschaffung und Analyse von Webinhalten
- **Forschungs-Agent**: Experte für die tiefgehende Analyse von Themen und Datenzusammenstellung

## Erste Schritte

### Systemanforderungen

- **Browser**: Chrome, Firefox, Safari, Edge (aktuelle Versionen)
- **Internetverbindung**: Breitbandverbindung empfohlen
- **Konto**: Gültiges Benutzerkonto im Agent-NN-System

### Installation

Agent-NN ist eine webbasierte Anwendung und erfordert keine lokale Installation. Für Unternehmenslösungen gibt es jedoch auch eine lokale Deployment-Option:

1. **Cloud-Version**: Besuchen Sie einfach [app.agent-nn.com](https://app.agent-nn.com) und melden Sie sich an
2. **Lokales Deployment**:
   - Docker installieren
   - Das Agent-NN-Image aus unserem privaten Repository herunterladen
   - Den Container mit den entsprechenden Umgebungsvariablen starten

### Anmeldung und Kontoeinrichtung

1. Besuchen Sie die Agent-NN-Website und klicken Sie auf "Anmelden"
2. Erstellen Sie ein neues Konto oder melden Sie sich mit bestehenden Anmeldedaten an
3. Füllen Sie Ihr Profil aus, um personalisierte Empfehlungen zu erhalten
4. Konfigurieren Sie Ihre bevorzugten Domänen und Interessen

![Anmeldeprozess](Anmeldeprozess.svg)

## Die Benutzeroberfläche

Die Agent-NN-Benutzeroberfläche ist intuitiv und benutzerfreundlich gestaltet, mit klaren Navigationselementen und einem zentralen Chat-Interface.

![Benutzeroberfläche](Benutzeroberfläche.svg)

### Hauptelemente

1. **Chat-Bereich**: Zentrales Element für die Kommunikation mit Agenten
2. **Agenten-Auswahl**: Seitenleiste zur direkten Auswahl bestimmter Agenten
3. **Wissensmanagement**: Bereich für die Verwaltung von Dokumenten und Wissensbasen
4. **Verlauf**: Zugriff auf frühere Konversationen und Ergebnisse
5. **Einstellungen**: Systemkonfiguration und Benutzerpräferenzen

### Tastenkombinationen

| Aktion | Windows | Mac |
|--------|---------|-----|
| Neue Konversation | Ctrl+N | Cmd+N |
| Agent wechseln | Ctrl+Tab | Cmd+Tab |
| Verlauf durchsuchen | Ctrl+H | Cmd+H |
| Hilfe aufrufen | F1 | F1 |
| Letzte Nachricht bearbeiten | Ctrl+E | Cmd+E |

## Mit Agenten interagieren

Die Interaktion mit Agent-NN erfolgt hauptsächlich über natürlichsprachliche Gespräche. Das System analysiert Ihre Anfragen und leitet sie an die am besten geeigneten Agenten weiter.

### Einen Chat starten

1. Öffnen Sie die Agent-NN-Anwendung
2. Klicken Sie auf "Neue Konversation" oder verwenden Sie die Tastenkombination Ctrl+N/Cmd+N
3. Beginnen Sie mit einer Nachricht an das System

![Chat-Interaktion](Chat-Interaktion.svg)

### Direkte Agentenwahl

Sie können auch direkt mit einem bestimmten Agenten sprechen:

1. Wählen Sie den gewünschten Agenten aus der Seitenleiste aus
2. Alternativ können Sie "@" gefolgt vom Agentennamen in Ihrer Nachricht verwenden, z.B. "@FinanzAgent"

### Aufgaben an Agenten delegieren

Agent-NN kann komplexe Aufgaben ausführen:

1. Beschreiben Sie klar die Aufgabe, die Sie erledigt haben möchten
2. Geben Sie relevante Details, Einschränkungen und Anforderungen an
3. Der Supervisor-Agent analysiert Ihre Anfrage und delegiert sie an den passenden Spezialisten
4. Bei Bedarf können Agenten Rückfragen stellen oder Klarstellungen erbitten

![Aufgabendelegation](Aufgabendelegation.svg)

### Multi-Agent-Zusammenarbeit

Für komplexe Aufgaben können mehrere Agenten zusammenarbeiten:

1. Stellen Sie eine komplexe Anfrage, die verschiedene Domänen umfasst
2. Das System koordiniert automatisch mehrere Agenten
3. Die Agenten kommunizieren untereinander, um eine vollständige Lösung zu erarbeiten
4. Das System präsentiert Ihnen die integrierte Antwort
---
---
---

# Agent-NN: Benutzerhandbuch

## Inhaltsverzeichnis

1. [Einführung](#einführung)
2. [Systemüberblick](#systemüberblick)
3. [Erste Schritte](#erste-schritte)
4. [Die Benutzeroberfläche](#die-benutzeroberfläche)
5. [Mit Agenten interagieren](#mit-agenten-interagieren)
6. [Domänenspezifische Agenten](#domänenspezifische-agenten)
7. [Wissensmanagement](#wissensmanagement)
8. [Erweiterte Funktionen](#erweiterte-funktionen)
9. [Fehlerbehebung](#fehlerbehebung)
10. [Häufig gestellte Fragen](#häufig-gestellte-fragen)
11. [Kontakt und Support](#kontakt-und-support)

## Einführung

Willkommen bei Agent-NN, Ihrem fortschrittlichen Multi-Agent-System für domänenspezifische Assistenz und Aufgabenautomatisierung. Agent-NN kombiniert die Leistungsfähigkeit von modernen Sprachmodellen mit spezialisierten Wissensbasen, um maßgeschneiderte Hilfe in verschiedenen Fachbereichen anzubieten.

Diese Dokumentation führt Sie durch alle Funktionen und Möglichkeiten des Systems und zeigt Ihnen, wie Sie von der Leistungsfähigkeit spezialisierter KI-Agenten profitieren können.

### Was ist Agent-NN?

Agent-NN ist ein intelligentes Assistenzsystem, das unterschiedliche spezialisierte Agenten für verschiedene Wissensbereiche und Aufgabentypen koordiniert. Anders als herkömmliche KI-Assistenten, die als Generalisten arbeiten, bietet Agent-NN Zugang zu maßgeschneiderten Experten für Bereiche wie Finanzen, Technologie, Marketing und mehr.

### Hauptmerkmale

- **Domänenspezifische Expertise**: Spezialisierte Agenten für verschiedene Fachbereiche
- **Kollaborative Intelligenz**: Agenten, die zusammenarbeiten, um komplexe Aufgaben zu lösen
- **Kontinuierliche Verbesserung**: Agenten, die aus Interaktionen lernen und sich verbessern
- **Wissensbasierte Antworten**: Präzise Antworten basierend auf verifiziertem Fachwissen
- **Web-Integration**: Automatische Datenerfassung und -aktualisierung aus dem Web

## Systemüberblick

Agent-NN besteht aus mehreren Hauptkomponenten, die zusammenarbeiten, um Ihnen ein leistungsstarkes Assistenzsystem zu bieten.

![Systemarchitektur](Systemarchitektur.svg)

### Hauptkomponenten

1. **Chatbot-Interface**: Ihr Haupteinstiegspunkt für die Interaktion mit dem System
2. **Supervisor-Agent**: Analysiert Anfragen und leitet sie an die passenden Spezialisten weiter
3. **Fach-Agenten**: Spezialisierte Experten für verschiedene Wissensdomänen
4. **Wissensbasen**: Domänenspezifische Informationsquellen für fundierte Antworten
5. **Web-Crawler**: System für die automatische Aktualisierung von Informationen

### Agententypen

Agent-NN bietet verschiedene Arten von Agenten, jeder mit einzigartigen Fähigkeiten:

![Agententypen](Agententypen.svg)

- **Finanz-Agent**: Experte für Finanzanalyse, Investitionen und Finanzplanung
- **Tech-Agent**: Spezialist für Softwareentwicklung, Systemarchitektur und technische Problemlösung
- **Marketing-Agent**: Experte für Marketingstrategien, digitales Marketing und Markenentwicklung
- **Web-Agent**: Spezialist für die Beschaffung und Analyse von Webinhalten
- **Forschungs-Agent**: Experte für die tiefgehende Analyse von Themen und Datenzusammenstellung

## Erste Schritte

### Systemanforderungen

- **Browser**: Chrome, Firefox, Safari, Edge (aktuelle Versionen)
- **Internetverbindung**: Breitbandverbindung empfohlen
- **Konto**: Gültiges Benutzerkonto im Agent-NN-System

### Installation

Agent-NN ist eine webbasierte Anwendung und erfordert keine lokale Installation. Für Unternehmenslösungen gibt es jedoch auch eine lokale Deployment-Option:

1. **Cloud-Version**: Besuchen Sie einfach [app.Agent-NN.com](https://app.Agent-NN.com) und melden Sie sich an
2. **Lokales Deployment**:
   - Docker installieren
   - Das Agent-NN-Image aus unserem privaten Repository herunterladen
   - Den Container mit den entsprechenden Umgebungsvariablen starten

### Anmeldung und Kontoeinrichtung

1. Besuchen Sie die Agent-NN-Website und klicken Sie auf "Anmelden"
2. Erstellen Sie ein neues Konto oder melden Sie sich mit bestehenden Anmeldedaten an
3. Füllen Sie Ihr Profil aus, um personalisierte Empfehlungen zu erhalten
4. Konfigurieren Sie Ihre bevorzugten Domänen und Interessen

![Anmeldeprozess](Anmeldeprozess.svg)

## Die Benutzeroberfläche

Die Agent-NN-Benutzeroberfläche ist intuitiv und benutzerfreundlich gestaltet, mit klaren Navigationselementen und einem zentralen Chat-Interface.

![Benutzeroberfläche](Benutzeroberfläche.svg)

### Hauptelemente

1. **Chat-Bereich**: Zentrales Element für die Kommunikation mit Agenten
2. **Agenten-Auswahl**: Seitenleiste zur direkten Auswahl bestimmter Agenten
3. **Wissensmanagement**: Bereich für die Verwaltung von Dokumenten und Wissensbasen
4. **Verlauf**: Zugriff auf frühere Konversationen und Ergebnisse
5. **Einstellungen**: Systemkonfiguration und Benutzerpräferenzen

### Tastenkombinationen

| Aktion | Windows | Mac |
|--------|---------|-----|
| Neue Konversation | Ctrl+N | Cmd+N |
| Agent wechseln | Ctrl+Tab | Cmd+Tab |
| Verlauf durchsuchen | Ctrl+H | Cmd+H |
| Hilfe aufrufen | F1 | F1 |
| Letzte Nachricht bearbeiten | Ctrl+E | Cmd+E |

## Mit Agenten interagieren

Die Interaktion mit Agent-NN erfolgt hauptsächlich über natürlichsprachliche Gespräche. Das System analysiert Ihre Anfragen und leitet sie an die am besten geeigneten Agenten weiter.

### Einen Chat starten

1. Öffnen Sie die Agent-NN-Anwendung
2. Klicken Sie auf "Neue Konversation" oder verwenden Sie die Tastenkombination Ctrl+N/Cmd+N
3. Beginnen Sie mit einer Nachricht an das System

![Chat-Interaktion](Chat-Interaktion.svg)

### Direkte Agentenwahl

Sie können auch direkt mit einem bestimmten Agenten sprechen:

1. Wählen Sie den gewünschten Agenten aus der Seitenleiste aus
2. Alternativ können Sie "@" gefolgt vom Agentennamen in Ihrer Nachricht verwenden, z.B. "@FinanzAgent"

### Aufgaben an Agenten delegieren

Agent-NN kann komplexe Aufgaben ausführen:

1. Beschreiben Sie klar die Aufgabe, die Sie erledigt haben möchten
2. Geben Sie relevante Details, Einschränkungen und Anforderungen an
3. Der Supervisor-Agent analysiert Ihre Anfrage und delegiert sie an den passenden Spezialisten
4. Bei Bedarf können Agenten Rückfragen stellen oder Klarstellungen erbitten

![Aufgabendelegation](Aufgabendelegation.svg)

### Multi-Agent-Zusammenarbeit

Für komplexe Aufgaben können mehrere Agenten zusammenarbeiten:

1. Stellen Sie eine komplexe Anfrage, die verschiedene Domänen umfasst
2. Das System koordiniert automatisch mehrere Agenten
3. Die Agenten kommunizieren untereinander, um eine vollständige Lösung zu erarbeiten
4. Das System präsentiert Ihnen die integrierte Antwort

## Domänenspezifische Agenten

Agent-NN bietet spezialisierte Agenten für verschiedene Domänen, jeder mit eigenen Fähigkeiten und Expertisebereichen.

### Finanz-Agent

Der Finanz-Agent ist Ihr Experte für alle finanzbezogenen Fragen und Aufgaben.

**Hauptfähigkeiten:**
- Finanzanalyse und Berichterstattung
- Investitionsstrategie und Portfoliomanagement
- Risikobewertung und -management
- Budgetierung und Prognose
- Steuerplanung und Compliance
- Finanzmodellierung und Bewertung

**Beispielanfragen:**
- "Analysiere diese Bilanz und gib mir Einblicke"
- "Erstelle eine Investitionsstrategie basierend auf meinem Risikoprofil"
- "Entwickle eine Finanzprognose für mein Startup"
- "Berechne wichtige Finanzkennzahlen für dieses Unternehmen"

![Finanz-Agent](Finanz-Agent.svg)

### Tech-Agent

Der Tech-Agent ist Ihr Spezialist für technische Fragen und Softwareentwicklung.

**Hauptfähigkeiten:**
- Softwareentwicklung und -architektur
- Systemdesign und -integration
- Technische Problemlösung
- Code-Review und -optimierung
- Technologie-Stack-Bewertung
- Leistungsoptimierung

**Beispielanfragen:**
- "Entwirf eine Systemarchitektur für Skalierbarkeit"
- "Überprüfe und optimiere diesen Code"
- "Implementiere Sicherheits-Best-Practices in meinem System"
- "Hilf mir bei der Fehlerbehebung dieses technischen Problems"

![Tech-Agent](Tech-Agent.svg)

### Marketing-Agent

Der Marketing-Agent ist Ihr Experte für Marketingstrategien und Kundenkommunikation.

**Hauptfähigkeiten:**
- Entwicklung von Marketingstrategien
- Planung digitaler Marketingkampagnen
- Markenentwicklung und -management
- Marktanalyse und -forschung
- Kundensegmentierung
- Marketing-Analytik

**Beispielanfragen:**
- "Entwickle eine umfassende Marketingstrategie"
- "Erstelle eine digitale Marketingkampagne"
- "Analysiere Markttrends und Wettbewerb"
- "Entwirf ein Kundenbindungsprogramm"

> TODO: Bild einfügen: ./marketing_agent.png

### Web-Agent

Der Web-Agent ist spezialisiert auf die Beschaffung und Analyse von Webinhalten.

**Hauptfähigkeiten:**
- Web-Scraping und Datenextraktion
- Automatisierte Webrecherche
- Inhaltszusammenfassung
- Datenanalyse aus Webquellen

**Beispielanfragen:**
- "Sammle Informationen über dieses Thema aus aktuellen Webquellen"
- "Verfolge die Entwicklung dieses Aktienkurses in Echtzeit"
- "Fasse die neuesten Nachrichten zu diesem Thema zusammen"

## Wissensmanagement

Agent-NN ermöglicht es Ihnen, eigene Dokumente und Wissensquellen zu verwalten, die die Agenten in ihren Analysen und Antworten berücksichtigen können.

### Dokumente hochladen

1. Navigieren Sie zum Abschnitt "Wissensmanagement"
2. Klicken Sie auf "Neues Dokument hinzufügen"
3. Wählen Sie die Datei von Ihrem Gerät aus (unterstützte Formate: PDF, DOCX, TXT, CSV)
4. Ordnen Sie das Dokument einer oder mehreren Domänen zu
5. Fügen Sie optionale Metadaten hinzu, um die Auffindbarkeit zu verbessern

![Dokumentenupload](Dokumentenupload.svg)

### Wissensbasen verwalten

1. Gehen Sie zum Bereich "Wissensbasen"
2. Hier sehen Sie alle Ihre erstellten Wissenssammlungen
3. Sie können neue Wissensbasen erstellen, bestehende bearbeiten oder löschen
4. Agenten können auf relevante Wissensbasen zugreifen, wenn sie Ihre Anfragen beantworten

### Web-Quellen integrieren

Sie können Agenten anweisen, spezifische Webquellen zu überwachen und zu integrieren:

1. Navigieren Sie zu "Web-Integration"
2. Fügen Sie URLs hinzu, die regelmäßig überprüft werden sollen
3. Legen Sie Aktualisierungsintervalle fest
4. Die Informationen werden automatisch in die relevanten Wissensbasen aufgenommen

![Web-Integration](Web-Integration.svg)

## Erweiterte Funktionen

Agent-NN bietet zahlreiche erweiterte Funktionen für Benutzer, die das volle Potenzial des Systems ausschöpfen möchten.

### Automatisierte Workflows

Sie können wiederkehrende Aufgaben automatisieren:

1. Gehen Sie zu "Workflows" im Hauptmenü
2. Klicken Sie auf "Neuer Workflow"
3. Definieren Sie Auslöser (zeitbasiert, ereignisbasiert)
4. Konfigurieren Sie die auszuführenden Aufgaben
5. Legen Sie Benachrichtigungspräferenzen fest

![Workflow-Erstellung](Workflow-Erstellung.svg)

### Benutzerdefinierte Agenten

Fortgeschrittene Benutzer können eigene spezialisierte Agenten erstellen:

1. Gehen Sie zu "Erweiterte Einstellungen" > "Benutzerdefinierte Agenten"
2. Klicken Sie auf "Neuer Agent"
3. Definieren Sie den Fokusbereich und die Fähigkeiten
4. Weisen Sie Wissensquellen zu
5. Konfigurieren Sie Spezialparameter

### Integrationen

Agent-NN kann mit verschiedenen externen Systemen integriert werden:

- **API-Zugriff**: Nutzen Sie unsere REST-API für Systemintegration
- **Websocket-Verbindungen**: Für Echtzeitkommunikation
- **Webhook-Benachrichtigungen**: Für ereignisbasierte Automatisierung
- **Drittanbieter-Apps**: Verbindung zu Slack, Teams, Trello und mehr

![Integrationsoptionen](Integrationsoptionen.svg)

### Erweiterte Analysen

Erhalten Sie Einblicke in die Nutzung und Leistung des Systems:

1. Navigieren Sie zu "Analysen" im Hauptmenü
2. Sehen Sie Nutzungsstatistiken und Interaktionsmuster
3. Überwachen Sie die Leistung verschiedener Agenten
4. Identifizieren Sie Verbesserungsmöglichkeiten

## Fehlerbehebung

Hier finden Sie Lösungen für häufig auftretende Probleme.

### Verbindungsprobleme

**Problem**: Agent-NN reagiert nicht oder lädt nicht vollständig.

**Lösungen**:
1. Überprüfen Sie Ihre Internetverbindung
2. Löschen Sie den Browser-Cache und laden Sie die Seite neu
3. Versuchen Sie, einen anderen Browser zu verwenden
4. Überprüfen Sie, ob der Agent-NN-Dienst unter [status.Agent-NN.com](https://status.Agent-NN.com) aktiv ist

### Agenten-Auswahl

**Problem**: Der falsche Agent wird für meine Anfrage ausgewählt.

**Lösungen**:
1. Formulieren Sie Ihre Anfrage präziser
2. Verwenden Sie direkte Agentenzuweisung mit "@AgentName"
3. Geben Sie zusätzlichen Kontext, um die Absicht zu verdeutlichen
4. Geben Sie Feedback, damit das System lernen kann

![Fehlerbehebung Agenten-Auswahl](FehlerbehebungAgenten-Auswahl.svg)

### Langsame Antworten

**Problem**: Agenten benötigen zu lange für Antworten.

**Lösungen**:
1. Vereinfachen Sie komplexe Anfragen in kleinere Teilfragen
2. Überprüfen Sie Ihre Internetverbindung
3. Vermeiden Sie Spitzenzeiten mit hoher Systemauslastung
4. Für lokale Deployments: Überprüfen Sie die Ressourcenzuweisung

### Unerwartete Antworten

**Problem**: Agenten geben irrelevante oder falsche Antworten.

**Lösungen**:
1. Geben Sie mehr Kontext in Ihrer Anfrage
2. Stellen Sie Klarstellungsfragen
3. Bitten Sie um Überprüfung oder Neuformulierung
4. Geben Sie Feedback zur Antwortqualität

## Häufig gestellte Fragen

### Allgemeine Fragen

**F: Wie unterscheidet sich Agent-NN von herkömmlichen KI-Assistenten?**

A: Agent-NN bietet domänenspezifische Expertise durch spezialisierte Agenten, die für bestimmte Wissensgebiete optimiert sind, im Gegensatz zu Allzweck-Assistenten.

**F: Kann ich Agent-NN offline nutzen?**

A: Für Unternehmenslösungen ist ein lokales Deployment möglich, aber eine Internetverbindung kann für bestimmte Funktionen wie Web-Recherche erforderlich sein.

**F: Wie sicher sind meine Daten bei Agent-NN?**

A: Agent-NN verwendet Verschlüsselung auf Unternehmensebene und strikte Datenschutzprotokolle. Unternehmensdaten werden nie für das Training der Modelle verwendet, es sei denn, dies wurde ausdrücklich genehmigt.

### Technische Fragen

**F: Welche Dateiformate unterstützt Agent-NN?**

A: Agent-NN unterstützt PDF, DOCX, TXT, CSV, MD, HTML, PPTX, XLSX und andere gängige Formate.

**F: Gibt es eine Begrenzung für die Upload-Größe?**

A: Standardmäßig liegt das Limit bei 50 MB pro Datei, Unternehmenskunden können höhere Limits anfordern.

**F: Kann ich Agent-NN in meine bestehenden Systeme integrieren?**

A: Ja, Agent-NN bietet umfangreiche API- und Webhook-Schnittstellen für die Integration in Ihre bestehenden Workflows und Systeme.

### Abonnement und Preise

**F: Welche Abonnementpläne gibt es?**

A: Agent-NN bietet verschiedene Pläne von Einzelnutzern bis zu Unternehmensabonnements. Besuchen Sie unsere [Preisseite](https://Agent-NN.com/pricing) für aktuelle Informationen.

**F: Kann ich Agent-NN testen, bevor ich kaufe?**

A: Ja, wir bieten eine 14-tägige kostenlose Testversion mit vollständigem Funktionsumfang an.

**F: Gibt es Beschränkungen für die Anzahl der Anfragen?**

A: Je nach Abonnementplan gibt es unterschiedliche Limits für die Anzahl der Anfragen und die Komplexität der Aufgaben.

## Kontakt und Support

Bei Fragen oder Problemen stehen wir Ihnen gerne zur Verfügung.

### Support-Kanäle

- **E-Mail**: support@Agent-NN.com
- **Live-Chat**: Verfügbar während der Geschäftszeiten über die Agent-NN-Website
- **Telefon**: +49 123 456 7890 (Mo-Fr, 9-17 Uhr MEZ)
- **Wissensdatenbank**: [help.Agent-NN.com](https://help.Agent-NN.com)

### Feedback geben

Wir schätzen Ihr Feedback! Sie können Vorschläge einreichen:

1. Über die Feedback-Schaltfläche in der Anwendung
2. Per E-Mail an feedback@Agent-NN.com
3. Über unser [Feedback-Portal](https://feedback.Agent-NN.com)

### Community

Treten Sie unserer Community bei, um mehr zu erfahren und sich mit anderen Nutzern auszutauschen:

- **Forum**: [community.Agent-NN.com](https://community.Agent-NN.com)
- **GitHub**: [github.com/Agent-NN](https://github.com/Agent-NN)
- **Twitter**: [@Agent-NNAI](https://twitter.com/Agent-NNAI)
- **LinkedIn**: [linkedin.com/company/Agent-NN](https://linkedin.com/company/Agent-NN)

---

© 2025 Agent-NN AI GmbH. Alle Rechte vorbehalten.
