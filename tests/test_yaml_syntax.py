"""
Regressionstests: YAML-Syntax aller Konfigurationsdateien.

Prüft, dass alle .yaml-Dateien valides YAML sind und
keine offensichtlichen Strukturprobleme haben.
"""
import pytest
import yaml
from pathlib import Path

HA_CONFIG_DIR = Path("C:/Projekte/homeassistant")

# Alle YAML-Dateien die getestet werden sollen
YAML_FILES = (
    list(HA_CONFIG_DIR.glob("*.yaml"))
    + list((HA_CONFIG_DIR / "packages").glob("*.yaml"))
)


def yaml_file_ids(files):
    return [f.name for f in files]


@pytest.mark.parametrize("yaml_file", YAML_FILES, ids=yaml_file_ids(YAML_FILES))
def test_yaml_is_valid(yaml_file):
    """Jede YAML-Datei muss syntaktisch korrekt parsebar sein."""
    content = yaml_file.read_text(encoding="utf-8")
    # !secret und !include_dir_* Tags durch Platzhalter ersetzen
    content = _replace_ha_tags(content)
    try:
        result = yaml.safe_load(content)
    except yaml.YAMLError as e:
        pytest.fail(f"{yaml_file.name}: YAML-Syntaxfehler: {e}")


# Dateien, die leer sein dürfen (HA-Platzhalter)
ALLOWED_EMPTY = {"scenes.yaml", "scripts.yaml", "customize.yaml"}


@pytest.mark.parametrize("yaml_file", YAML_FILES, ids=yaml_file_ids(YAML_FILES))
def test_yaml_not_empty(yaml_file):
    """YAML-Dateien dürfen nicht leer sein – außer bekannte Platzhalter."""
    if yaml_file.name in ALLOWED_EMPTY:
        pytest.skip(f"{yaml_file.name} darf als Platzhalter leer sein")
    content = yaml_file.read_text(encoding="utf-8").strip()
    assert content, f"{yaml_file.name} ist leer"


def test_all_expected_package_files_exist():
    """Alle erwarteten Package-Dateien müssen vorhanden sein."""
    expected = [
        "alphaess_customize.yaml",
        "evcc_bridge.yaml",
        "klima_sensoren.yaml",
        "signal_monitoring.yaml",
        "vicare_tkol.yaml",
        "vitoconnect_monitoring.yaml",
        "waermepumpe_management.yaml",
    ]
    packages_dir = HA_CONFIG_DIR / "packages"
    for filename in expected:
        assert (packages_dir / filename).exists(), (
            f"Erwartete Package-Datei fehlt: {filename}"
        )


def test_configuration_yaml_exists():
    assert (HA_CONFIG_DIR / "configuration.yaml").exists()


def test_automations_yaml_exists():
    assert (HA_CONFIG_DIR / "automations.yaml").exists()


def test_scripts_yaml_exists():
    assert (HA_CONFIG_DIR / "scripts.yaml").exists()


def test_scenes_yaml_exists():
    assert (HA_CONFIG_DIR / "scenes.yaml").exists()


def _replace_ha_tags(content: str) -> str:
    """Ersetzt HA-spezifische YAML-Tags durch gültige Platzhalter für den Parser."""
    import re
    # !secret foo -> "__SECRET__"
    content = re.sub(r"!secret\s+\S+", '"__SECRET__"', content)
    # !include foo -> "__INCLUDE__"
    content = re.sub(r"!include\S*\s+\S+", '"__INCLUDE__"', content)
    # !include_dir_merge_named foo -> "__INCLUDE__"
    content = re.sub(r"!include\S+", '"__INCLUDE__"', content)
    return content