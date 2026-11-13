"""Colour space conversions used by the engine.

Display RGB is treated as sRGB-encoded Rec.709 primaries. The same curve is used
on the way in and on the way out of every LUT, so the choice only decides in
which space the perceptual statistics are measured.
"""

import numpy as np

_LINEAR_TO_LMS = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ]
)
_LMS_TO_OKLAB = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ]
)
_LMS_TO_LINEAR = np.linalg.inv(_LINEAR_TO_LMS)
_OKLAB_TO_LMS = np.linalg.inv(_LMS_TO_OKLAB)

_LINEAR_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)
_D65_WHITE = _LINEAR_TO_XYZ.sum(axis=1)
_LAB_EPSILON = (6.0 / 29.0) ** 3
_LAB_SLOPE = 1.0 / (3.0 * (6.0 / 29.0) ** 2)


def srgb_to_linear(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    magnitude = np.abs(rgb)
    linear = np.where(magnitude <= 0.04045, magnitude / 12.92, ((magnitude + 0.055) / 1.055) ** 2.4)

    return np.sign(rgb) * linear


def linear_to_srgb(linear):
    linear = np.asarray(linear, dtype=np.float64)
    magnitude = np.abs(linear)
    encoded = np.where(magnitude <= 0.0031308, magnitude * 12.92, 1.055 * magnitude ** (1.0 / 2.4) - 0.055)

    return np.sign(linear) * encoded


def linear_to_oklab(linear):
    lms = np.asarray(linear, dtype=np.float64) @ _LINEAR_TO_LMS.T

    return np.cbrt(lms) @ _LMS_TO_OKLAB.T


def oklab_to_linear(oklab):
    lms_root = np.asarray(oklab, dtype=np.float64) @ _OKLAB_TO_LMS.T

    return (lms_root ** 3) @ _LMS_TO_LINEAR.T


def rgb_to_oklab(rgb):
    return linear_to_oklab(srgb_to_linear(rgb))


def oklab_to_rgb(oklab):
    return linear_to_srgb(oklab_to_linear(oklab))


def rgb_to_cielab(rgb):
    xyz = srgb_to_linear(rgb) @ _LINEAR_TO_XYZ.T
    scaled = xyz / _D65_WHITE
    f = np.where(scaled > _LAB_EPSILON, np.cbrt(scaled), scaled * _LAB_SLOPE + 4.0 / 29.0)
    lightness = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])

    return np.stack([lightness, a, b], axis=-1)


def delta_e_2000(lab_first, lab_second):
    """CIEDE2000 colour difference between two arrays of CIELAB values."""
    l1, a1, b1 = np.moveaxis(np.asarray(lab_first, dtype=np.float64), -1, 0)
    l2, a2, b2 = np.moveaxis(np.asarray(lab_second, dtype=np.float64), -1, 0)

    chroma_mean = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2.0
    chroma_mean_7 = chroma_mean ** 7
    g = 0.5 * (1.0 - np.sqrt(chroma_mean_7 / (chroma_mean_7 + 25.0 ** 7)))
    a1_prime = a1 * (1.0 + g)
    a2_prime = a2 * (1.0 + g)
    c1_prime = np.hypot(a1_prime, b1)
    c2_prime = np.hypot(a2_prime, b2)
    h1_prime = np.degrees(np.arctan2(b1, a1_prime)) % 360.0
    h2_prime = np.degrees(np.arctan2(b2, a2_prime)) % 360.0

    delta_l = l2 - l1
    delta_c = c2_prime - c1_prime
    chroma_product = c1_prime * c2_prime
    hue_difference = h2_prime - h1_prime
    hue_difference = np.where(hue_difference > 180.0, hue_difference - 360.0, hue_difference)
    hue_difference = np.where(hue_difference < -180.0, hue_difference + 360.0, hue_difference)
    hue_difference = np.where(chroma_product == 0.0, 0.0, hue_difference)
    delta_h = 2.0 * np.sqrt(chroma_product) * np.sin(np.radians(hue_difference) / 2.0)

    l_mean = (l1 + l2) / 2.0
    c_mean_prime = (c1_prime + c2_prime) / 2.0
    hue_sum = h1_prime + h2_prime
    hue_mean = np.where(
        np.abs(h1_prime - h2_prime) > 180.0,
        np.where(hue_sum < 360.0, (hue_sum + 360.0) / 2.0, (hue_sum - 360.0) / 2.0),
        hue_sum / 2.0,
    )
    hue_mean = np.where(chroma_product == 0.0, hue_sum, hue_mean)

    t = (
        1.0
        - 0.17 * np.cos(np.radians(hue_mean - 30.0))
        + 0.24 * np.cos(np.radians(2.0 * hue_mean))
        + 0.32 * np.cos(np.radians(3.0 * hue_mean + 6.0))
        - 0.20 * np.cos(np.radians(4.0 * hue_mean - 63.0))
    )
    delta_theta = 30.0 * np.exp(-(((hue_mean - 275.0) / 25.0) ** 2))
    c_mean_prime_7 = c_mean_prime ** 7
    rotation_chroma = 2.0 * np.sqrt(c_mean_prime_7 / (c_mean_prime_7 + 25.0 ** 7))
    l_offset = (l_mean - 50.0) ** 2
    weight_l = 1.0 + (0.015 * l_offset) / np.sqrt(20.0 + l_offset)
    weight_c = 1.0 + 0.045 * c_mean_prime
    weight_h = 1.0 + 0.015 * c_mean_prime * t
    rotation = -np.sin(np.radians(2.0 * delta_theta)) * rotation_chroma

    term_l = delta_l / weight_l
    term_c = delta_c / weight_c
    term_h = delta_h / weight_h

    return np.sqrt(term_l ** 2 + term_c ** 2 + term_h ** 2 + rotation * term_c * term_h)


def mean_delta_e(rgb_first, rgb_second):
    return float(np.mean(delta_e_2000(rgb_to_cielab(rgb_first), rgb_to_cielab(rgb_second))))
