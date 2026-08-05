"""
Regressionstests: Jinja2-Template-Logik der HA-Konfiguration.

Simuliert HA-Template-Auswertung mit einer minimalen Jinja2-Umgebung
und prüft, dass die Templates korrekte Ergebnisse liefern.
"""
import pytest
from jinja2 import Environment


# ---------------------------------------------------------------------------
# Hilfs-Fixture: minimale HA-ähnliche Jinja2-Umgebung
# ---------------------------------------------------------------------------

def make_env(states_dict: dict) -> Environment:
    """
    Erstellt eine Jinja2-Umgebung mit `states()` und `is_state()` Funktionen,
    die aus dem übergebenen Dict lesen – analog zu HA.
    """
    env = Environment()

    def states(entity_id):
        return str(states_dict.get(entity_id, "unknown"))

    def is_state(entity_id, value):
        return states_dict.get(entity_id) == value

    def state_attr(entity_id, attribute):
        key = f"{entity_id}.{attribute}"
        return states_dict.get(key)

    env.globals["states"] = states
    env.globals["is_state"] = is_state
    env.globals["state_attr"] = state_attr

    return env


def render(template_str: str, states_dict: dict) -> str:
    env = make_env(states_dict)
    return env.from_string(template_str).render().strip()


# ---------------------------------------------------------------------------
# evcc_bridge.yaml – EV Charger Current per Phase
# ---------------------------------------------------------------------------

EV_CURRENT_TEMPLATE = """
{% set phase_state = states('select.alpha_ess_charger_alp2021082020071_ev_charger_phases') %}
{% set phases = 1 if '1' in phase_state else 3 %}
{% set power = states('sensor.alb002022080906_pev') | float(0) %}
{% if power > 50 %}
  {{ (power / (230 * phases)) | round(2) }}
{% else %}
  0
{% endif %}
"""


class TestEvChargerCurrentTemplate:
    def test_einphasig_mit_leistung(self):
        result = render(EV_CURRENT_TEMPLATE, {
            "select.alpha_ess_charger_alp2021082020071_ev_charger_phases": "1-phasig",
            "sensor.alb002022080906_pev": "2300",
        })
        assert result == "10.0", f"Erwartet 10.0, erhalten: {result}"

    def test_dreiphasig_mit_leistung(self):
        result = render(EV_CURRENT_TEMPLATE, {
            "select.alpha_ess_charger_alp2021082020071_ev_charger_phases": "3-phasig",
            "sensor.alb002022080906_pev": "6900",
        })
        assert result == "10.0", f"Erwartet 10.0, erhalten: {result}"

    def test_keine_leistung_liefert_null(self):
        result = render(EV_CURRENT_TEMPLATE, {
            "select.alpha_ess_charger_alp2021082020071_ev_charger_phases": "1-phasig",
            "sensor.alb002022080906_pev": "0",
        })
        assert result == "0"

    def test_unter_schwellwert_liefert_null(self):
        """Leistung <= 50W soll 0 ergeben (Standby-Filter)."""
        result = render(EV_CURRENT_TEMPLATE, {
            "select.alpha_ess_charger_alp2021082020071_ev_charger_phases": "1-phasig",
            "sensor.alb002022080906_pev": "50",
        })
        assert result == "0"

    def test_unavailable_leistung_liefert_null(self):
        result = render(EV_CURRENT_TEMPLATE, {
            "select.alpha_ess_charger_alp2021082020071_ev_charger_phases": "1-phasig",
            "sensor.alb002022080906_pev": "unavailable",
        })
        assert result == "0"


# ---------------------------------------------------------------------------
# evcc_bridge.yaml – Charger Status Mapping (EVSE-Zustände)
# ---------------------------------------------------------------------------

CHARGER_STATUS_TEMPLATE = """
{% set s = states('sensor.alb002022080906_ev_charger_status_raw') %}
{% if s == '1' %} A {% elif s in ['2', '6'] %} B {% elif s in ['3', '4', '5'] %} C {% else %} F {% endif %}
"""


class TestChargerStatusTemplate:
    def test_status_1_ist_A(self):
        result = render(CHARGER_STATUS_TEMPLATE,
                        {"sensor.alb002022080906_ev_charger_status_raw": "1"})
        assert result == "A"

    def test_status_2_ist_B(self):
        result = render(CHARGER_STATUS_TEMPLATE,
                        {"sensor.alb002022080906_ev_charger_status_raw": "2"})
        assert result == "B"

    def test_status_6_ist_B(self):
        result = render(CHARGER_STATUS_TEMPLATE,
                        {"sensor.alb002022080906_ev_charger_status_raw": "6"})
        assert result == "B"

    def test_status_3_ist_C(self):
        result = render(CHARGER_STATUS_TEMPLATE,
                        {"sensor.alb002022080906_ev_charger_status_raw": "3"})
        assert result == "C"

    def test_status_4_ist_C(self):
        result = render(CHARGER_STATUS_TEMPLATE,
                        {"sensor.alb002022080906_ev_charger_status_raw": "4"})
        assert result == "C"

    def test_status_5_ist_C(self):
        result = render(CHARGER_STATUS_TEMPLATE,
                        {"sensor.alb002022080906_ev_charger_status_raw": "5"})
        assert result == "C"

    def test_status_unbekannt_ist_F(self):
        result = render(CHARGER_STATUS_TEMPLATE,
                        {"sensor.alb002022080906_ev_charger_status_raw": "99"})
        assert result == "F"

    def test_status_unavailable_ist_F(self):
        result = render(CHARGER_STATUS_TEMPLATE,
                        {"sensor.alb002022080906_ev_charger_status_raw": "unavailable"})
        assert result == "F"


# ---------------------------------------------------------------------------
# evcc_bridge.yaml – Charger Enabled Mapping
# ---------------------------------------------------------------------------

CHARGER_ENABLED_TEMPLATE = """
{% set s = states('sensor.alb002022080906_ev_charger_status_raw') %}
{% if s in ['3', '4', '5'] %} true {% else %} false {% endif %}
"""


class TestChargerEnabledTemplate:
    def test_laden_aktiv_ist_true(self):
        for status in ["3", "4", "5"]:
            result = render(CHARGER_ENABLED_TEMPLATE,
                            {"sensor.alb002022080906_ev_charger_status_raw": status})
            assert result == "true", f"Status {status} sollte true liefern"

    def test_nicht_laden_ist_false(self):
        for status in ["1", "2", "6", "unavailable"]:
            result = render(CHARGER_ENABLED_TEMPLATE,
                            {"sensor.alb002022080906_ev_charger_status_raw": status})
            assert result == "false", f"Status {status} sollte false liefern"


# ---------------------------------------------------------------------------
# evcc_bridge.yaml – Heizung Preset Mapping
# ---------------------------------------------------------------------------

HEIZUNG_PRESET_TEMPLATE = """
{% if trigger_payload == '1' %} eco {% elif trigger_payload == '3' %} comfort {% else %} home {% endif %}
"""


class TestHeizungPresetTemplate:
    def test_payload_1_ist_eco(self):
        env = Environment()
        result = env.from_string(HEIZUNG_PRESET_TEMPLATE).render(
            trigger_payload="1").strip()
        assert result == "eco"

    def test_payload_3_ist_comfort(self):
        env = Environment()
        result = env.from_string(HEIZUNG_PRESET_TEMPLATE).render(
            trigger_payload="3").strip()
        assert result == "comfort"

    def test_payload_2_ist_home(self):
        env = Environment()
        result = env.from_string(HEIZUNG_PRESET_TEMPLATE).render(
            trigger_payload="2").strip()
        assert result == "home"

    def test_payload_off_ist_home(self):
        env = Environment()
        result = env.from_string(HEIZUNG_PRESET_TEMPLATE).render(
            trigger_payload="off").strip()
        assert result == "home"


# ---------------------------------------------------------------------------
# evcc_bridge.yaml – Heizung Mode State Mapping
# ---------------------------------------------------------------------------

HEIZUNG_MODE_STATE_TEMPLATE = """
{% set m = preset_mode %}
{% if m == 'eco' %} 1 {% elif m == 'comfort' %} 3 {% else %} 2 {% endif %}
"""


class TestHeizungModeStateTemplate:
    def test_eco_ist_1(self):
        env = Environment()
        result = env.from_string(HEIZUNG_MODE_STATE_TEMPLATE).render(
            preset_mode="eco").strip()
        assert result == "1"

    def test_comfort_ist_3(self):
        env = Environment()
        result = env.from_string(HEIZUNG_MODE_STATE_TEMPLATE).render(
            preset_mode="comfort").strip()
        assert result == "3"

    def test_home_ist_2(self):
        env = Environment()
        result = env.from_string(HEIZUNG_MODE_STATE_TEMPLATE).render(
            preset_mode="home").strip()
        assert result == "2"


# ---------------------------------------------------------------------------
# waermepumpe_management.yaml – WP Power Templates
# ---------------------------------------------------------------------------

WP_HEIZUNG_POWER_TEMPLATE = """
{{ 3680 if is_state('binary_sensor.wp_status_heizbetrieb', 'on') else 0 }}
"""

WP_WARMWASSER_POWER_TEMPLATE = """
{{ 5600 if is_state('binary_sensor.wp_status_warmwasserbetrieb', 'on') else 0 }}
"""


class TestWpPowerTemplates:
    def test_heizung_an_liefert_3680w(self):
        result = render(WP_HEIZUNG_POWER_TEMPLATE,
                        {"binary_sensor.wp_status_heizbetrieb": "on"})
        assert result == "3680"

    def test_heizung_aus_liefert_0w(self):
        result = render(WP_HEIZUNG_POWER_TEMPLATE,
                        {"binary_sensor.wp_status_heizbetrieb": "off"})
        assert result == "0"

    def test_warmwasser_an_liefert_5600w(self):
        result = render(WP_WARMWASSER_POWER_TEMPLATE,
                        {"binary_sensor.wp_status_warmwasserbetrieb": "on"})
        assert result == "5600"

    def test_warmwasser_aus_liefert_0w(self):
        result = render(WP_WARMWASSER_POWER_TEMPLATE,
                        {"binary_sensor.wp_status_warmwasserbetrieb": "off"})
        assert result == "0"


# ---------------------------------------------------------------------------
# waermepumpe_management.yaml – WP Status Binary Sensors
# ---------------------------------------------------------------------------

WP_HEIZBETRIEB_TEMPLATE = """
{{ is_state('binary_sensor.cu401b_g_kompressor', 'on') and
   is_state('binary_sensor.cu401b_g_ww_aufladung', 'off') }}
"""

WP_WARMWASSERBETRIEB_TEMPLATE = """
{{ is_state('binary_sensor.cu401b_g_kompressor', 'on') and
   is_state('binary_sensor.cu401b_g_ww_aufladung', 'on') }}
"""


class TestWpStatusTemplates:
    def test_heizbetrieb_wenn_kompressor_an_und_ww_aus(self):
        result = render(WP_HEIZBETRIEB_TEMPLATE, {
            "binary_sensor.cu401b_g_kompressor": "on",
            "binary_sensor.cu401b_g_ww_aufladung": "off",
        })
        assert result == "True"

    def test_kein_heizbetrieb_wenn_kompressor_aus(self):
        result = render(WP_HEIZBETRIEB_TEMPLATE, {
            "binary_sensor.cu401b_g_kompressor": "off",
            "binary_sensor.cu401b_g_ww_aufladung": "off",
        })
        assert result == "False"

    def test_kein_heizbetrieb_wenn_ww_aktiv(self):
        result = render(WP_HEIZBETRIEB_TEMPLATE, {
            "binary_sensor.cu401b_g_kompressor": "on",
            "binary_sensor.cu401b_g_ww_aufladung": "on",
        })
        assert result == "False"

    def test_warmwasserbetrieb_wenn_kompressor_und_ww_an(self):
        result = render(WP_WARMWASSERBETRIEB_TEMPLATE, {
            "binary_sensor.cu401b_g_kompressor": "on",
            "binary_sensor.cu401b_g_ww_aufladung": "on",
        })
        assert result == "True"

    def test_kein_warmwasserbetrieb_wenn_nur_kompressor(self):
        result = render(WP_WARMWASSERBETRIEB_TEMPLATE, {
            "binary_sensor.cu401b_g_kompressor": "on",
            "binary_sensor.cu401b_g_ww_aufladung": "off",
        })
        assert result == "False"


# ---------------------------------------------------------------------------
# alphaess_customize.yaml – kWp-Normierung Templates
# ---------------------------------------------------------------------------

CARPORT_KWP_TEMPLATE = """
{{ (states('sensor.alphaess_tagliche_carport_produktion') | float(0) / 6.560) | round(2) }}
"""

DACH_KWP_TEMPLATE = """
{{ (states('sensor.alphaess_tagliche_dach_produktion') | float(0) / 9.840) | round(2) }}
"""

GARAGE_KWP_TEMPLATE = """
{{ (states('sensor.alphaess_tagliche_garage_produktion') | float(0) / 4.920) | round(2) }}
"""


class TestKwpNormierungTemplates:
    def test_carport_volle_leistung(self):
        result = render(CARPORT_KWP_TEMPLATE,
                        {"sensor.alphaess_tagliche_carport_produktion": "6.56"})
        assert result == "1.0"

    def test_dach_volle_leistung(self):
        result = render(DACH_KWP_TEMPLATE,
                        {"sensor.alphaess_tagliche_dach_produktion": "9.84"})
        assert result == "1.0"

    def test_garage_volle_leistung(self):
        result = render(GARAGE_KWP_TEMPLATE,
                        {"sensor.alphaess_tagliche_garage_produktion": "4.92"})
        assert result == "1.0"

    def test_carport_unavailable_liefert_null(self):
        result = render(CARPORT_KWP_TEMPLATE,
                        {"sensor.alphaess_tagliche_carport_produktion": "unavailable"})
        assert result == "0.0"

    def test_dach_halbvolle_leistung(self):
        result = render(DACH_KWP_TEMPLATE,
                        {"sensor.alphaess_tagliche_dach_produktion": "4.92"})
        assert result == "0.5"


# ---------------------------------------------------------------------------
# evcc_bridge.yaml – Heizungstemperatur mit Offset
# ---------------------------------------------------------------------------

HEIZUNG_TEMP_TEMPLATE = """
{% set aktuelle_temp = states('sensor.beheizte_raume_temperatur') | float(21.0) %}
{% set offset = states('input_number.heizung_evcc_offset') | float(0.0) %}
{{ (aktuelle_temp + offset) | round(1) }}
"""


class TestHeizungTempTemplate:
    def test_temp_ohne_offset(self):
        result = render(HEIZUNG_TEMP_TEMPLATE, {
            "sensor.beheizte_raume_temperatur": "21.5",
            "input_number.heizung_evcc_offset": "0.0",
        })
        assert result == "21.5"

    def test_temp_mit_positivem_offset(self):
        result = render(HEIZUNG_TEMP_TEMPLATE, {
            "sensor.beheizte_raume_temperatur": "21.5",
            "input_number.heizung_evcc_offset": "0.5",
        })
        assert result == "22.0"

    def test_temp_mit_negativem_offset(self):
        result = render(HEIZUNG_TEMP_TEMPLATE, {
            "sensor.beheizte_raume_temperatur": "21.5",
            "input_number.heizung_evcc_offset": "-0.5",
        })
        assert result == "21.0"

    def test_temp_unavailable_liefert_fallback(self):
        result = render(HEIZUNG_TEMP_TEMPLATE, {
            "sensor.beheizte_raume_temperatur": "unavailable",
            "input_number.heizung_evcc_offset": "0.0",
        })
        assert result == "21.0"


# ---------------------------------------------------------------------------
# waermepumpe_management.yaml – evcc Day/Night Mode Logik
# ---------------------------------------------------------------------------

EVCC_MODE_TEMPLATE = """
{{ 'pv' if sun_state == 'above_horizon' else 'off' }}
"""


class TestEvccDayNightMode:
    def test_tag_liefert_pv(self):
        env = Environment()
        result = env.from_string(EVCC_MODE_TEMPLATE).render(
            sun_state="above_horizon").strip()
        assert result == "pv"

    def test_nacht_liefert_off(self):
        env = Environment()
        result = env.from_string(EVCC_MODE_TEMPLATE).render(
            sun_state="below_horizon").strip()
        assert result == "off"


# ---------------------------------------------------------------------------
# evcc_bridge.yaml – Warmwasser Mode State
# ---------------------------------------------------------------------------

WW_MODE_TEMPLATE = """
{{ '3' if is_state('binary_sensor.cu401b_g_einmalige_ladung', 'on') else '2' }}
"""


class TestWarmwasserModeTemplate:
    def test_einmalige_ladung_aktiv_ist_3(self):
        result = render(WW_MODE_TEMPLATE,
                        {"binary_sensor.cu401b_g_einmalige_ladung": "on"})
        assert result == "3"

    def test_einmalige_ladung_inaktiv_ist_2(self):
        result = render(WW_MODE_TEMPLATE,
                        {"binary_sensor.cu401b_g_einmalige_ladung": "off"})
        assert result == "2"

    def test_unavailable_ist_2(self):
        result = render(WW_MODE_TEMPLATE,
                        {"binary_sensor.cu401b_g_einmalige_ladung": "unavailable"})
        assert result == "2"
