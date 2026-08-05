"""
Pytest-Konfiguration und gemeinsame Fixtures für HA-Regressionstests.
"""
import pytest
from pathlib import Path

# Pfad zur produktiven HA-Konfiguration
HA_CONFIG_DIR = Path("C:/Projekte/homeassistant")
PACKAGES_DIR = HA_CONFIG_DIR / "packages"


@pytest.fixture(scope="session")
def ha_config_dir():
    return HA_CONFIG_DIR


@pytest.fixture(scope="session")
def packages_dir():
    return PACKAGES_DIR


@pytest.fixture(scope="session")
def all_yaml_files(ha_config_dir):
    """Gibt alle YAML-Dateien der HA-Konfiguration zurück."""
    files = list(ha_config_dir.glob("*.yaml"))
    files += list((ha_config_dir / "packages").glob("*.yaml"))
    return files


@pytest.fixture(scope="session")
def all_package_files(packages_dir):
    return list(packages_dir.glob("*.yaml"))