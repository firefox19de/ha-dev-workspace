$workspace = Join-Path $PSScriptRoot '..\workspace\home-assistant-dev.code-workspace'

if (-not (Test-Path $workspace)) {
    Write-Error "Workspace-Datei nicht gefunden: $workspace"
    exit 1
}

Write-Host "Öffne Home Assistant Dev Workspace..."
Start-Process $workspace
