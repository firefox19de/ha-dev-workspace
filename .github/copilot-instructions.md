# Copilot Instructions – Home Assistant Dev Workspace

## Workspace-Überblick

Drei Repos, ein VS Code Workspace (`workspace/home-assistant-dev.code-workspace`):

| Repo | Pfad | Zweck |
|---|---|---|
| `homeassistant` | `C:/Projekte/homeassistant` | Produktive HA-Konfiguration (YAML) |
| `alphaess-wallbox` | `C:/Projekte/alphaess-wallbox` | Custom HACS-Integration (Python) |
| `ha-dev-workspace` | `C:/Projekte/ha-dev-workspace` | Tooling, Tests, Skripte |

Workspace öffnen: `./scripts/start-ha-dev.ps1` oder `workspace/home-assistant-dev.code-workspace` direkt.

---

## Repo 1: `homeassistant` – HA-Konfiguration

### Architektur & Datenfluss

```
EVCC ──MQTT──► evcc_bridge (packages/evcc_bridge.yaml)
                     │
       ┌─────────────┴──────────────┐
       ▼                            ▼
AlphaESS OpenAPI            alphaess_wallbox (Web-API)
(Start/Stop, Lesen)         (Phasen, Ampere, Modus schreiben)
       │
       └──► mqtt_statestream ──► EVCC
```

EVCC sendet Steuerkommandos an `ha_bridge/charger/…` Topics. HA publisht Zustand über `mqtt_statestream` zurück (Topics: `homeassistant/<domain>/…`).

### Struktur

- `configuration.yaml` – Einstiegspunkt; **nie direkt Logik eintragen**, alles über Packages
- `packages/` – Kernlogik, eine Datei pro Domäne:
  - `evcc_bridge.yaml` – MQTT-Bridge EVCC ↔ HA, Template-Sensoren
  - `waermepumpe_management.yaml` – Wärmepumpensteuerung, evcc Day/Night-Mode
  - `vicare_tkol.yaml` / `vitoconnect_monitoring.yaml` – Viessmann-Integration
  - `alphaess_customize.yaml`, `klima_sensoren.yaml`, `signal_monitoring.yaml`, `evcc_optimizer.yaml`
- `automations.yaml` – UI-verwaltete Automationen; **nicht manuell bearbeiten**
- `custom_components/` – HACS-Integrationen (inkl. `alphaess_wallbox`)
- `esphome/vicare-poti.yaml` – ESPHome-Device für Viessmann-Poti
- `secrets.yaml` – nie committen; CI erzeugt sie aus `secrets.yaml.example`

### Konventionen (YAML / Jinja2)

- **Neue Funktion → neues Package-File**; niemals direkt in `configuration.yaml`
- Template-Zahlen immer mit Fallback: `| float(0)` oder `| float(21.0)` – nie `| float` allein
- Standby-Filter: EV-Leistungen ≤ 50 W → Ergebnis ist `0` (explizite `{% if power > 50 %}` Guards)
- Phasen-Erkennung: `'1' in phase_state` prüft ob String „1" enthält (`1-phasig` vs. `3-phasig`)
- HA-Tags (`!secret`, `!include_dir_named`) sind in Packages valide; Tests ersetzen sie per Regex
- `scenes.yaml`, `scripts.yaml`, `customize.yaml` dürfen leer sein (bekannte Platzhalter)

### CI/CD & Debugging

CI (`.github/workflows/main.yml`): HA Docker-Image validiert Config bei jedem Push auf `main`:
```bash
docker run --rm -v ${{ github.workspace }}:/config \
  ghcr.io/home-assistant/home-assistant:stable \
  python3 -m homeassistant --config /config --script check_config
```

Debug-Logging im laufenden HA (Pfad-Mapping Add-on: `/homeassistant` statt `/config`):
```bash
ha core logs 2>&1 | grep -i alphaess
```
```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.alphaess_wallbox: debug
```
`_LOGGER.debug()` ist ohne explizites Level unsichtbar → `_LOGGER.info()` für dauerhaft sichtbare Logs.

---

## Repo 2: `alphaess-wallbox` – Custom Integration

### Architektur

```
config_flow.py  →  UI-Setup (Login-Test beim Einrichten)
__init__.py     →  Entry-Setup: Client + Coordinator erstellen, Platforms laden
api.py          →  AlphaWebApiClient: 3-stufiger Login, AES-Verschlüsselung
coordinator.py  →  DataUpdateCoordinator (60s Polling, Auto-Re-Login bei None)
select.py       →  AlphaESSModeSelect, AlphaESSPhaseSelect (CoordinatorEntity)
number.py       →  AlphaWallboxCurrentNumber (6–16 A Slider)
button.py       →  AlphaESSFetchStatusButton (Refresh-Trigger)
```

### Kritische Patterns

- **Passwort-Verschlüsselung**: AES-CBC, Key = `SHA256(username)`, IV = `MD5(username)` → `pycryptodome` Pflicht-Dependency (`requirements_test.txt` + `manifest.json`)
- **API-Schreibmuster**: `_update_ev_settings()` liest zuerst `get_ev_data()`, patcht nur Zielfelder, sendet vollständiges `oldPileData`-Objekt an `/api/iterate/newEv/setNewEv`
- **Optimistisches State-Update**: Nach `set_*()` → `coordinator.data` direkt mutieren + `async_write_ha_state()` + `async_request_refresh()` (kein Warten auf nächsten Poll)
- **Entity-Pattern**: Alle Entities erben `CoordinatorEntity` + HA-Basisklasse; `_attr_has_entity_name = True` + `_attr_translation_key` für i18n (Texte in `translations/de.json`, `translations/en.json`)
- **Re-Login**: Coordinator wirft `UpdateFailed` erst nach gescheitertem Re-Login, nicht sofort bei `None`
- **Config Flow**: `vol.Optional(CONF_URL)` mit `str` typisiert (nicht `vol.Url()`) – `vol.Url()` verursacht 500-Fehler in der HA-UI

### Entitäten & Mappings

| Entität | API-Feld | Wertebereich |
|---|---|---|
| `number.ev_charger_max_current_setting` | `maxCurrent` | 6–16 A (Slider) |
| `select.ev_charger_phases` | `chargingpilePhase` | `1-phasig`↔1 / `3-phasig`↔3 |
| `select.ev_charger_charge_mode` | `chargingmode` | 4 Modi (Code 1–4) |
| `button.ev_charger_refresh_status` | – | Coordinator-Refresh |

### Tests & CI/CD (`alphaess-wallbox`)

```powershell
cd C:/Projekte/alphaess-wallbox
.\.venv\Scripts\activate.ps1
$env:PYTHONPATH = "."; pytest tests/ -v
```

**Test-Patterns:**
- `FakeCoordinator` (`test_entities.py`) – Coordinator-Stub ohne HA-Laufzeit; `data={...}` vorbelegen
- `MockResponse` + `AsyncCallWrapper` (`test_api.py`) – simuliert aiohttp Context-Manager-Interface
- API-Tests: `client._request = AsyncMock(side_effect=[resp1, resp2])` für geordnete Antwortsequenzen
- Entity-Tests: Action aufrufen, dann `mock_api.set_*.assert_called_once_with(...)` prüfen

CI: Python 3.11, `PYTHONPATH=. pytest tests/` | **Release**: Tag `v*` → Manifest-Version automatisch gebumpt (nie manuell in `manifest.json` ändern)

---

## Tests für `homeassistant`-YAML (im `ha-dev-workspace`)

```powershell
cd C:/Projekte/ha-dev-workspace
.\.venv\Scripts\activate.ps1
pytest                               # alle Tests
pytest tests/test_templates.py -v   # Jinja2-Template-Logik
pytest tests/test_yaml_syntax.py -v # YAML-Syntax aller Package-Dateien
```

Tests lesen direkt aus `C:/Projekte/homeassistant` – Repo muss lokal vorhanden sein.

Template-Tests: Funktion `render(template_str, states_dict)` nutzen; `make_env()` simuliert `states()`, `is_state()`, `state_attr()`. Neue Tests als `class TestXyz:` strukturieren.

**Neue Package-Datei hinzufügen:**
1. `C:/Projekte/homeassistant/packages/<name>.yaml` anlegen
2. `test_yaml_syntax.py` → `test_all_expected_package_files_exist()` → Dateiname ergänzen
3. Template-Logik in `test_templates.py` als `class TestXyz:` testen

**Devcontainer**: Image `mcr.microsoft.com/devcontainers/python:3.11`, Post-Create: `pip install homeassistant pytest-homeassistant-custom-component`, Port 8123.
