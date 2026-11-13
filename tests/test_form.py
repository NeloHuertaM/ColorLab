import unittest

from colormatch.form import default_values, format_results, options_from_form, preset_values
from colormatch.workflow import ClipResult


class FormTests(unittest.TestCase):
    def test_given_default_values_when_mapping_then_options_are_a_full_strength_shot_match_on_the_last_node(self):
        # Act
        options = options_from_form(default_values())

        # Assert
        self.assertEqual(("match", 1, "", 0), (options.mode, options.track_index, options.clip_colour, options.node_index))
        self.assertEqual(("mkl", 1.0), (options.settings.method, options.settings.strength))

    def test_given_edited_values_when_mapping_then_percentages_become_fractions_and_choices_become_keys(self):
        # Arrange
        values = dict(
            default_values(),
            mode_index=1,
            reference_image='  "C:/looks/film.png" ',
            method_index=2,
            clip_colour_index=1,
            strength=40,
            skin=70,
            highlights=10,
        )

        # Act
        options = options_from_form(values)

        # Assert
        self.assertEqual(("look", "C:/looks/film.png", "Orange"), (options.mode, options.reference_image, options.clip_colour))
        self.assertEqual(
            ("reinhard", 0.4, 0.7, 0.1),
            (
                options.settings.method,
                options.settings.strength,
                options.settings.skin_protection,
                options.settings.highlight_protection,
            ),
        )

    def test_given_the_look_mode_when_reading_its_preset_then_uses_optimal_transport_with_skin_protection(self):
        # Act
        preset = preset_values(1)

        # Assert
        self.assertEqual({"method_index": 1, "skin": 50, "highlights": 50}, preset)

    def test_given_invalid_numbers_when_mapping_then_track_and_node_are_kept_in_range(self):
        # Arrange
        values = dict(default_values(), track=0, node=-3, lut_folder="  ")

        # Act
        options = options_from_form(values)

        # Assert
        self.assertEqual((1, 0), (options.track_index, options.node_index))
        self.assertTrue(options.lut_folder)

    def test_given_mixed_results_when_formatting_then_reports_the_count_and_each_clip(self):
        # Arrange
        results = [ClipResult("A", True, "ok"), ClipResult("B", False, "fallo")]

        # Act
        text = format_results(results)

        # Assert
        self.assertEqual("1 de 2 planos graduados.\nOK  A: ok\nERR B: fallo", text)
