"""Configuration and code generation for ES7210 digital gain and ALC."""

from collections.abc import Callable
from pathlib import Path

import pytest

from esphome.components.es7210.audio_adc import (
    ALC_SCHEMA,
    CONFIG_SCHEMA,
    validate_digital_gain,
)
import esphome.config_validation as cv


def test_defaults_preserve_fixed_unity_digital_gain() -> None:
    """Existing configurations leave ALC off and do not add digital boost."""
    config = CONFIG_SCHEMA({})
    assert config["digital_gain"] == 0
    assert config["alc"]["enabled"] is False


@pytest.mark.parametrize("gain", [-95.5, -0.5, 0, 12, 31.5, 32])
def test_digital_gain_range(gain: float) -> None:
    """Every half-dB setting is represented exactly by the codec."""
    assert validate_digital_gain(f"{gain}dB") == gain


@pytest.mark.parametrize("gain", [-96, 32.5, 0.25, float("nan"), float("inf")])
def test_invalid_digital_gain(gain: float) -> None:
    """Reject settings the codec cannot represent, including non-finite inputs."""
    with pytest.raises(cv.Invalid):
        validate_digital_gain(gain)


def test_alc_retains_independent_manual_gain() -> None:
    """ALC's ceiling and the value restored when it is disabled are separate."""
    config = CONFIG_SCHEMA(
        {"digital_gain": "6dB", "alc": {"enabled": True, "max_gain": "18dB"}}
    )
    assert config["digital_gain"] == 6
    assert config["alc"]["max_gain"] == 18


@pytest.mark.parametrize(
    "config",
    [
        {"min_level": "-6dB", "max_level": "-12dB"},
        {"min_level": "-10dB"},
        {"max_gain": "33dB"},
        {"ramp_rate": 16},
    ],
)
def test_invalid_alc_settings(config: dict) -> None:
    """The target band, gain ceiling and ramp rate must fit the hardware."""
    with pytest.raises(cv.Invalid):
        ALC_SCHEMA(config)


def test_gain_codegen(generate_main: Callable[[str | Path], str]) -> None:
    """Generate the manual value and the independent ALC configuration."""
    cpp = generate_main("tests/component_tests/es7210/test_es7210.yaml")
    assert "codec->set_digital_gain(6.0f);" in cpp
    assert "codec->set_alc_max_gain(12.0f);" in cpp
    assert "codec->set_alc_target(247);" in cpp
    assert "codec->set_alc_ramp_rate(6);" in cpp
    assert "codec->set_alc_enabled(true);" in cpp
