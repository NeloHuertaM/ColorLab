import unittest
from dataclasses import replace

import numpy as np

from colormatch.colorspace import mean_delta_e, rgb_to_oklab
from colormatch.engine import PRESETS, MatchError, MatchSettings, fit_correction
from colormatch.lut import apply_lut, lattice
from tests import synthetic

METHODS = ("reinhard", "mkl", "sliced")
NEUTRAL_CHROMA = 0.01


def _chroma(rgb):
    oklab = rgb_to_oklab(np.asarray(rgb).reshape(-1, 3))

    return np.hypot(oklab[:, 1], oklab[:, 2])


def _mean_oklab_distance(first, second):
    first_mean = rgb_to_oklab(first.reshape(-1, 3)).mean(axis=0)
    second_mean = rgb_to_oklab(second.reshape(-1, 3)).mean(axis=0)

    return float(np.linalg.norm(first_mean - second_mean))


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.reference = synthetic.scene()
        self.source = synthetic.graded(self.reference, white_balance=(1.25, 1.0, 0.75), exposure=0.6)

    def test_given_a_shot_with_a_cast_and_underexposure_when_matching_then_mean_delta_e_drops_by_70_percent(self):
        before = mean_delta_e(self.source, self.reference)

        for method in METHODS:
            with self.subTest(method=method):
                # Arrange
                settings = MatchSettings(method=method)

                # Act
                matched = fit_correction(self.source, self.reference, settings).apply_rgb(self.source)

                # Assert
                self.assertLess(mean_delta_e(matched, self.reference), 0.3 * before)

    def test_given_a_fitted_correction_when_baked_into_a_33_point_lut_then_the_lut_reproduces_the_match(self):
        for method in METHODS:
            with self.subTest(method=method):
                # Arrange
                correction = fit_correction(self.source, self.reference, MatchSettings(method=method))

                # Act
                via_lut = apply_lut(self.source, correction.to_lut())

                # Assert
                direct = correction.apply_rgb(self.source)
                self.assertLess(mean_delta_e(via_lut, direct), 0.5)
                self.assertLess(mean_delta_e(via_lut, self.reference), 0.3 * mean_delta_e(self.source, self.reference))

    def test_given_an_external_look_when_transferring_then_average_colour_moves_towards_the_look(self):
        # Arrange
        look = synthetic.teal_orange(synthetic.scene(height=80, width=80, seed=9)[::-1])
        settings = PRESETS["look"]

        # Act
        result = fit_correction(self.reference, look, settings).apply_rgb(self.reference)

        # Assert
        self.assertLess(_mean_oklab_distance(result, look), 0.3 * _mean_oklab_distance(self.reference, look))

    def test_given_strength_zero_when_building_the_lut_then_it_is_the_identity(self):
        # Arrange
        settings = MatchSettings(strength=0.0, highlight_protection=0.0)

        # Act
        table = fit_correction(self.source, self.reference, settings).to_lut()

        # Assert
        np.testing.assert_allclose(table, lattice(33), atol=1e-6)

    def test_given_half_strength_when_matching_then_result_lies_between_source_and_full_match(self):
        # Arrange
        full = fit_correction(self.source, self.reference, MatchSettings(strength=1.0)).apply_rgb(self.source)

        # Act
        half = fit_correction(self.source, self.reference, MatchSettings(strength=0.5)).apply_rgb(self.source)

        # Assert
        half_error = mean_delta_e(half, self.reference)
        self.assertLess(half_error, mean_delta_e(self.source, self.reference))
        self.assertGreater(half_error, mean_delta_e(full, self.reference))

    def test_given_the_same_inputs_when_fitting_twice_then_the_luts_are_identical(self):
        # Arrange
        settings = MatchSettings(method="sliced")

        # Act
        first = fit_correction(self.source, self.reference, settings).to_lut()
        second = fit_correction(self.source, self.reference, settings).to_lut()

        # Assert
        np.testing.assert_array_equal(first, second)

    def test_given_a_grey_ramp_when_matching_then_lightness_stays_monotonic(self):
        # Arrange
        ramp = np.linspace(0.0, 1.0, 256)[np.newaxis, :, np.newaxis].repeat(3, axis=2)

        for method in METHODS:
            with self.subTest(method=method):
                correction = fit_correction(self.source, self.reference, MatchSettings(method=method))

                # Act
                lightness = rgb_to_oklab(correction.apply_rgb(ramp).reshape(-1, 3))[:, 0]

                # Assert
                self.assertTrue(np.all(np.diff(lightness) >= -1e-6))

    def test_given_skin_protection_when_transferring_a_strong_look_then_skin_hue_shifts_less(self):
        # Arrange
        look = synthetic.teal_orange(synthetic.scene(seed=5))
        skin = np.array([[synthetic.SKIN_TONE]])
        unprotected_settings = replace(PRESETS["look"], skin_protection=0.0)
        protected_settings = replace(PRESETS["look"], skin_protection=1.0)

        # Act
        unprotected = fit_correction(self.reference, look, unprotected_settings).apply_rgb(skin)
        protected = fit_correction(self.reference, look, protected_settings).apply_rgb(skin)

        # Assert
        self.assertLess(mean_delta_e(protected, skin), mean_delta_e(unprotected, skin))

    def test_given_highlight_protection_when_the_look_has_tinted_highlights_then_white_stays_neutral(self):
        # Arrange
        look = synthetic.teal_orange(synthetic.scene(seed=5))
        white = np.array([[[0.98, 0.98, 0.98]]])
        unprotected_settings = replace(PRESETS["look"], highlight_protection=0.0)
        protected_settings = replace(PRESETS["look"], highlight_protection=1.0)

        # Act
        unprotected = fit_correction(self.reference, look, unprotected_settings).apply_rgb(white)
        protected = fit_correction(self.reference, look, protected_settings).apply_rgb(white)

        # Assert
        self.assertLess(_chroma(protected)[0], NEUTRAL_CHROMA)
        self.assertGreater(_chroma(unprotected)[0], _chroma(protected)[0])

    def test_given_a_flat_source_frame_when_matching_then_the_lut_is_finite_and_in_range(self):
        for value in (0.0, 0.5, 1.0):
            with self.subTest(value=value):
                # Arrange
                source = synthetic.flat(value)

                # Act
                table = fit_correction(source, self.reference).to_lut()

                # Assert
                self.assertTrue(np.all(np.isfinite(table)))
                self.assertGreaterEqual(table.min(), 0.0)
                self.assertLessEqual(table.max(), 1.0)

    def test_given_a_single_pixel_source_when_matching_then_returns_a_valid_lut(self):
        # Arrange
        source = np.array([[[0.3, 0.4, 0.5]]])

        # Act
        table = fit_correction(source, self.reference).to_lut()

        # Assert
        self.assertTrue(np.all(np.isfinite(table)))

    def test_given_a_monochrome_reference_when_matching_a_colour_shot_then_output_is_near_neutral(self):
        # Arrange
        monochrome = self.reference.mean(axis=-1, keepdims=True).repeat(3, axis=-1)

        # Act
        result = fit_correction(self.reference, monochrome).apply_rgb(self.reference)

        # Assert
        self.assertLess(float(np.mean(_chroma(result))), 0.25 * float(np.mean(_chroma(self.reference))))

    def test_given_a_monochrome_source_when_matching_a_colour_reference_then_output_is_finite_and_tinted_towards_it(self):
        # Arrange
        monochrome = self.reference.mean(axis=-1, keepdims=True).repeat(3, axis=-1)

        # Act
        result = fit_correction(monochrome, self.reference).apply_rgb(monochrome)

        # Assert
        self.assertTrue(np.all(np.isfinite(result)))
        self.assertLess(_mean_oklab_distance(result, self.reference), _mean_oklab_distance(monochrome, self.reference))

    def test_given_a_flat_reference_when_matching_then_raises_match_error(self):
        # Act & Assert
        with self.assertRaises(MatchError):
            fit_correction(self.source, synthetic.flat(0.4))

    def test_given_non_finite_pixels_when_matching_then_raises_match_error(self):
        # Arrange
        broken = self.source.copy()
        broken[0, 0, 0] = np.nan

        # Act & Assert
        with self.assertRaises(MatchError):
            fit_correction(broken, self.reference)

    def test_given_a_greyscale_array_when_matching_then_raises_match_error(self):
        # Act & Assert
        with self.assertRaises(MatchError):
            fit_correction(self.source[..., 0], self.reference)

    def test_given_an_unknown_method_when_matching_then_raises_match_error(self):
        # Act & Assert
        with self.assertRaises(MatchError):
            fit_correction(self.source, self.reference, MatchSettings(method="neural"))

    def test_given_out_of_range_settings_when_validating_then_values_are_clamped(self):
        # Arrange
        settings = MatchSettings(strength=3.0, skin_protection=-1.0, sliced_iterations=0)

        # Act
        validated = settings.validated()

        # Assert
        self.assertEqual((1.0, 0.0, 1), (validated.strength, validated.skin_protection, validated.sliced_iterations))
