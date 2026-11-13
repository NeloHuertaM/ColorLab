import unittest

import numpy as np

from colormatch.colorspace import (
    delta_e_2000,
    linear_to_srgb,
    mean_delta_e,
    oklab_to_rgb,
    rgb_to_cielab,
    rgb_to_oklab,
    srgb_to_linear,
)

SHARMA_PAIRS = [
    ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
    ((50.0, 0.0, 0.0), (50.0, -1.0, 2.0), 2.3669),
    ((50.0, 2.5, 0.0), (73.0, 25.0, -18.0), 27.1492),
    ((2.0776, 0.0795, -1.135), (0.9033, -0.0636, -0.5514), 0.9082),
]


class ColorspaceTests(unittest.TestCase):
    def test_given_published_pairs_when_computing_delta_e_2000_then_matches_reference_values(self):
        for first, second, expected in SHARMA_PAIRS:
            with self.subTest(first=first, second=second):
                # Act
                actual = delta_e_2000(np.array(first), np.array(second))

                # Assert
                self.assertAlmostEqual(expected, float(actual), places=3)

    def test_given_random_colours_when_round_tripping_through_oklab_then_returns_the_input(self):
        # Arrange
        colours = np.random.default_rng(1).uniform(0.0, 1.0, size=(500, 3))

        # Act
        round_trip = oklab_to_rgb(rgb_to_oklab(colours))

        # Assert
        np.testing.assert_allclose(round_trip, colours, atol=1e-9)

    def test_given_display_white_when_converting_then_oklab_and_cielab_are_neutral_and_full_lightness(self):
        # Arrange
        white = np.array([[1.0, 1.0, 1.0]])

        # Act
        oklab = rgb_to_oklab(white)
        cielab = rgb_to_cielab(white)

        # Assert
        np.testing.assert_allclose(oklab, [[1.0, 0.0, 0.0]], atol=1e-4)
        np.testing.assert_allclose(cielab, [[100.0, 0.0, 0.0]], atol=1e-2)

    def test_given_encoded_values_when_round_tripping_the_transfer_curve_then_returns_the_input(self):
        # Arrange
        encoded = np.linspace(-0.1, 1.2, 50)

        # Act
        round_trip = linear_to_srgb(srgb_to_linear(encoded))

        # Assert
        np.testing.assert_allclose(round_trip, encoded, atol=1e-12)

    def test_given_identical_images_when_measuring_mean_delta_e_then_returns_zero(self):
        # Arrange
        image = np.random.default_rng(2).uniform(0.0, 1.0, size=(8, 8, 3))

        # Act
        difference = mean_delta_e(image, image)

        # Assert
        self.assertAlmostEqual(0.0, difference, places=9)
