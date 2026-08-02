$workspace = Join-Path $PSScriptRoot '..\workspace\home-assistant-dev.code-workspace'
if (Test-Path $workspace) {
    Start-Process $workspace
} else {
    Write-Error "Workspace-Datei nicht gefunden: $workspace"
}
