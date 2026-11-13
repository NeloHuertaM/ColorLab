"""Deterministic synthetic frames for the tests."""

import numpy as np

from colormatch.colorspace import linear_to_srgb, srgb_to_linear

SKIN_TONE = (0.86, 0.65, 0.53)


def scene(height=96, width=128, seed=3):
    random = np.random.default_rng(seed)
    rows = np.linspace(0.0, 1.0, height)[:, np.newaxis]
    columns = np.linspace(0.0, 1.0, width)[np.newaxis, :]
    red = 0.15 + 0.7 * columns + 0.0 * rows
    green = 0.2 + 0.6 * rows + 0.0 * columns
    blue = 0.25 + 0.5 * (1.0 - columns) * (1.0 - rows)
    image = np.stack([red, green, blue], axis=-1)
    image[10:40, 10:50] = (0.75, 0.2, 0.15)
    image[50:80, 20:60] = (0.15, 0.45, 0.2)
    image[20:70, 80:110] = SKIN_TONE
    image += random.normal(scale=0.02, size=image.shape)

    return np.clip(image, 0.0, 1.0)


def graded(image, white_balance=(1.0, 1.0, 1.0), exposure=1.0, gamma=1.0):
    """Simulates a different camera setting: white balance and exposure in linear light."""
    linear = srgb_to_linear(image) * np.asarray(white_balance) * exposure
    encoded = linear_to_srgb(np.clip(linear, 0.0, None)) ** gamma

    return np.clip(encoded, 0.0, 1.0)


def teal_orange(image):
    """A stylised look with a different content than the scene: warm highlights, cool shadows."""
    luminance = image.mean(axis=-1, keepdims=True)
    warm = np.array([1.0, 0.75, 0.45])
    cool = np.array([0.2, 0.45, 0.55])

    return np.clip(luminance * warm + (1.0 - luminance) * cool * 0.6, 0.0, 1.0)


def flat(value, height=32, width=32):
    return np.full((height, width, 3), value, dtype=np.float64)
