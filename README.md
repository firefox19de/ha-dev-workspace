# Home Assistant Dev Workspace

Dieses Repository dient als gemeinsamer Workspace und Tooling-Ordner für die Arbeit mit:
- alphaess-wallbox
- homeassistant

Zweck:
- gemeinsame VS Code Workspace-Konfiguration
- kleine Helper-Skripte und Notizen
- zentrale Struktur für lokale Entwicklungsarbeit

## Struktur

- .vscode/          VS Code Einstellungen und Empfohlene Erweiterungen
- scripts/          kleine Hilfsskripte
- docs/             Hinweise und Workflows
- workspace/        optional lokale Workspace-Dateien oder Vorlagen

## Startoptionen

### 1. Workspace direkt öffnen

Öffne die Datei [workspace/home-assistant-dev.code-workspace](workspace/home-assistant-dev.code-workspace).

### 2. Über das Skript starten

Im PowerShell-Terminal:

```powershell
./scripts/start-ha-dev.ps1
```

### 3. Mit Devcontainer arbeiten

Wenn du VS Code mit Dev Containers verwenden möchtest, öffne den Ordner in VS Code und wähle „Reopen in Container“.

Weitere Hinweise findest du in [docs/devcontainer-guide.md](docs/devcontainer-guide.md) und [docs/setup-guide.md](docs/setup-guide.md).
