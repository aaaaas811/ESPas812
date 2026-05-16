# BME690 MCP Server - wraps BME690 environmental sensor functionality
from fastmcp import FastMCP
import sys
import logging
import random
import math
import time

logger = logging.getLogger('BME690-MCP')

if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

mcp = FastMCP("BME690-Sensor")


# ---------------------------------------------------------------------------
# Simulation mode — generates realistic sensor data for development/testing
# ---------------------------------------------------------------------------

class BME690Simulator:
    """Simulates BME690 + BSEC output with realistic values."""

    def __init__(self):
        self._t = 0.0
        self._base_temp = 25.0
        self._base_hum = 50.0
        self._base_pres = 101325.0
        self._base_gas = 50000.0
        self._iaq_state = 25.0

    def _drift(self, speed=0.02, magnitude=1.0):
        self._t += speed
        return math.sin(self._t) * magnitude + random.gauss(0, 0.1)

    def read_raw(self) -> dict:
        raw_temp = self._base_temp + self._drift(0.03, 2.0) + random.gauss(0, 0.05)
        raw_pres = self._base_pres + self._drift(0.01, 50.0) + random.gauss(0, 2.0)
        raw_hum = self._base_hum + self._drift(0.02, 3.0) + random.gauss(0, 0.2)
        raw_hum = max(0, min(100, raw_hum))
        raw_gas = self._base_gas + self._drift(0.04, 15000.0) + random.gauss(0, 200.0)
        raw_gas = max(5000, raw_gas)

        self._iaq_state += random.gauss(0, 1.5)
        self._iaq_state = max(0, min(500, self._iaq_state))

        iaq = self._iaq_state
        static_iaq = iaq * 0.85 + random.gauss(0, 2)
        co2_eq = 400 + (iaq / 500.0) * 2300 + random.gauss(0, 20)
        breath_voc = (iaq / 500.0) * 4.5 + random.gauss(0, 0.05)

        temp_comp = raw_temp + 5.0 + random.gauss(0, 0.02)
        hum_comp = raw_hum * 0.95 + random.gauss(0, 0.1)

        return {
            "raw_temperature_C": round(raw_temp, 2),
            "raw_pressure_Pa": round(raw_pres, 1),
            "raw_humidity_pct": round(raw_hum, 2),
            "raw_gas_resistance_ohm": round(raw_gas, 1),
            "temperature_C": round(temp_comp, 2),
            "humidity_pct": round(hum_comp, 2),
            "pressure_hPa": round(raw_pres / 100.0, 2),
            "iaq": round(iaq, 1),
            "iaq_accuracy": random.choices([0, 1, 2, 3], weights=[5, 15, 30, 50])[0],
            "static_iaq": round(static_iaq, 1),
            "co2_equivalent_ppm": round(co2_eq, 1),
            "breath_voc_equivalent_ppm": round(breath_voc, 3),
        }


_sim = BME690Simulator()


# ---------------------------------------------------------------------------
# IAQ interpretation helpers — from factory_demo Temperature::getIAQLevel
# ---------------------------------------------------------------------------

def get_iaq_level(iaq: float) -> str:
    if iaq <= 50:       return "Excellent"
    elif iaq <= 100:    return "Good"
    elif iaq <= 150:    return "Fair"
    elif iaq <= 200:    return "Poor"
    elif iaq <= 300:    return "Bad"
    else:               return "Very Bad"


def get_humidity_comfort(humidity_pct: float) -> str:
    if 30 <= humidity_pct <= 60:
        return "Comfortable"
    elif 20 <= humidity_pct < 30 or 60 < humidity_pct <= 70:
        return "Moderate"
    else:
        return "Uncomfortable"


def get_pressure_trend(pressure_hpa: float) -> str:
    standard = 1013.25
    diff = pressure_hpa - standard
    if diff > 5:
        return "High (maybe Sunny)"
    elif diff < -5:
        return "Low (maybe Rainy)"
    else:
        return "Normal"


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def read_bme690_all() -> dict:
    """Read all BME690 sensor data at once. Returns raw & BSEC-compensated values:
temperature, humidity, pressure, gas resistance, IAQ, CO2 equivalent, breath VOC,
with comfort/quality assessments."""
    data = _sim.read_raw()

    return {
        "raw": {
            "temperature_C": data["raw_temperature_C"],
            "pressure_Pa": data["raw_pressure_Pa"],
            "humidity_pct": data["raw_humidity_pct"],
            "gas_resistance_ohm": data["raw_gas_resistance_ohm"],
        },
        "compensated": {
            "temperature_C": data["temperature_C"],
            "humidity_pct": data["humidity_pct"],
            "pressure_hPa": data["pressure_hPa"],
        },
        "air_quality": {
            "iaq": data["iaq"],
            "iaq_accuracy": data["iaq_accuracy"],
            "iaq_level": get_iaq_level(data["iaq"]),
            "static_iaq": data["static_iaq"],
            "co2_equivalent_ppm": data["co2_equivalent_ppm"],
            "breath_voc_equivalent_ppm": data["breath_voc_equivalent_ppm"],
        },
        "assessment": {
            "air_quality_level": get_iaq_level(data["iaq"]),
            "humidity_comfort": get_humidity_comfort(data["humidity_pct"]),
            "pressure_trend": get_pressure_trend(data["pressure_hPa"]),
        },
    }


@mcp.tool()
def read_bme690_temperature() -> dict:
    """Read BME690 heat-compensated temperature (degree Celsius)."""
    data = _sim.read_raw()
    return {
        "temperature_C": data["temperature_C"],
        "raw_temperature_C": data["raw_temperature_C"],
    }


@mcp.tool()
def read_bme690_humidity() -> dict:
    """Read BME690 heat-compensated humidity (%)."""
    data = _sim.read_raw()
    return {
        "humidity_pct": data["humidity_pct"],
        "raw_humidity_pct": data["raw_humidity_pct"],
        "comfort_level": get_humidity_comfort(data["humidity_pct"]),
    }


@mcp.tool()
def read_bme690_pressure() -> dict:
    """Read BME690 atmospheric pressure (hPa)."""
    data = _sim.read_raw()
    return {
        "pressure_hPa": data["pressure_hPa"],
        "raw_pressure_Pa": data["raw_pressure_Pa"],
        "trend": get_pressure_trend(data["pressure_hPa"]),
    }


@mcp.tool()
def read_bme690_air_quality() -> dict:
    """Read BME690 air quality: IAQ, CO2 equivalent, breath VOC equivalent."""
    data = _sim.read_raw()
    return {
        "iaq": data["iaq"],
        "iaq_accuracy": data["iaq_accuracy"],
        "iaq_level": get_iaq_level(data["iaq"]),
        "static_iaq": data["static_iaq"],
        "co2_equivalent_ppm": data["co2_equivalent_ppm"],
        "breath_voc_equivalent_ppm": data["breath_voc_equivalent_ppm"],
    }


@mcp.tool()
def read_bme690_gas_resistance() -> dict:
    """Read BME690 gas resistance (ohm), useful for VOC/gas detection."""
    data = _sim.read_raw()
    return {"gas_resistance_ohm": data["raw_gas_resistance_ohm"]}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting BME690 MCP Server (simulation mode)")
    mcp.run(transport="stdio")
