# Setup Guide für das Home Assistant Dev Workspace

## Voraussetzungen

- VS Code installiert
- Die beiden Repositories sind lokal vorhanden:
  - alphaess-wallbox
  - homeassistant
- Optional: Python-Extension und Home Assistant VS Code Extension

## Workspace öffnen

1. Öffne die Datei [workspace/home-assistant-dev.code-workspace](../workspace/home-assistant-dev.code-workspace).
2. VS Code öffnet den gemeinsamen Workspace mit allen drei Ordnern.
3. Falls die Ordner nicht als Roots erscheinen, prüfe die Pfade in der Workspace-Datei.

## Praktische Hinweise

- Für Python-Analyse sind die Custom-Components-Pfade bereits konfiguriert.
- Die empfohlenen Erweiterungen werden über die Workspace-Erweiterungen mitgeliefert.
- Das Skript [scripts/open-workspace.ps1](../scripts/open-workspace.ps1) öffnet den Workspace direkt.

## Nützliche nächste Schritte

- Home Assistant-Entwicklung in dem Repository homeassistant starten
- Custom Component-Entwicklung im Ordner alphaess-wallbox testen
- Bei Bedarf zusätzliche Aufgaben wie Test- oder Debug-Konfiguration ergänzen
