"""Masks that keep skin tones and highlights safe from aggressive transfers."""

import numpy as np

_SKIN_HUE_DEGREES = 58.0
_SKIN_HUE_HALF_WIDTH_DEGREES = 28.0
_SKIN_CHROMA_RANGE = (0.015, 0.035, 0.16, 0.22)
_SKIN_LIGHTNESS_RANGE = (0.20, 0.35, 0.90, 0.97)
_HIGHLIGHT_START = 0.80
_HIGHLIGHT_FULL = 0.97
_SHOULDER_KNEE = 0.85
_LIGHTNESS_CEILING = 1.0


def skin_weight(oklab):
    """Likelihood in [0, 1] that an Oklab colour is a skin tone."""
    lightness = oklab[:, 0]
    chroma = np.hypot(oklab[:, 1], oklab[:, 2])
    hue = np.degrees(np.arctan2(oklab[:, 2], oklab[:, 1]))
    hue_distance = np.abs((hue - _SKIN_HUE_DEGREES + 180.0) % 360.0 - 180.0)
    hue_weight = np.where(
        hue_distance < _SKIN_HUE_HALF_WIDTH_DEGREES,
        0.5 + 0.5 * np.cos(np.pi * hue_distance / _SKIN_HUE_HALF_WIDTH_DEGREES),
        0.0,
    )

    return hue_weight * _trapezoid(chroma, _SKIN_CHROMA_RANGE) * _trapezoid(lightness, _SKIN_LIGHTNESS_RANGE)


def highlight_weight(oklab):
    return _smoothstep(_HIGHLIGHT_START, _HIGHLIGHT_FULL, oklab[:, 0])


def protect(original, transferred, skin_amount, highlight_amount):
    """Blends the transferred colours back towards safe values.

    Skin keeps its original hue and chroma but follows the new lightness, so a
    look can change exposure without shifting faces. Highlights keep their
    original chroma (no tinted whites) and get a soft shoulder instead of a
    hard clip. Both blends are monotonic in lightness, so they cannot invert
    contrast.
    """
    result = transferred.copy()

    if skin_amount > 0.0:
        weight = (skin_amount * skin_weight(original))[:, np.newaxis]
        result[:, 1:] += weight * (original[:, 1:] - result[:, 1:])

    if highlight_amount > 0.0:
        weight = (highlight_amount * highlight_weight(original))[:, np.newaxis]
        result[:, 1:] += weight * (original[:, 1:] - result[:, 1:])
        result[:, 0] += highlight_amount * (_soft_shoulder(result[:, 0]) - result[:, 0])

    return result


def _soft_shoulder(lightness):
    headroom = _LIGHTNESS_CEILING - _SHOULDER_KNEE
    compressed = _SHOULDER_KNEE + headroom * np.tanh((lightness - _SHOULDER_KNEE) / headroom)

    return np.where(lightness > _SHOULDER_KNEE, compressed, lightness)


def _smoothstep(edge_low, edge_high, values):
    t = np.clip((values - edge_low) / (edge_high - edge_low), 0.0, 1.0)

    return t * t * (3.0 - 2.0 * t)


def _trapezoid(values, edges):
    rise_start, rise_end, fall_start, fall_end = edges

    return _smoothstep(rise_start, rise_end, values) * (1.0 - _smoothstep(fall_start, fall_end, values))
