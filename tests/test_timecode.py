import unittest

from colormatch.timecode import frames_to_timecode, parse_frame_rate


class TimecodeTests(unittest.TestCase):
    def test_given_non_drop_rates_when_converting_frames_then_returns_smpte_timecode(self):
        cases = [
            (86400, 24.0, "01:00:00:00"),
            (90000 + 37, 25.0, "01:00:01:12"),
            (86400 + 23, 23.976, "01:00:00:23"),
            (0, 30.0, "00:00:00:00"),
        ]

        for frame, rate, expected in cases:
            with self.subTest(frame=frame, rate=rate):
                # Act
                timecode = frames_to_timecode(frame, rate)

                # Assert
                self.assertEqual(expected, timecode)

    def test_given_drop_frame_rates_when_converting_frames_then_skips_dropped_labels(self):
        cases = [
            (1799, 29.97, "00:00:59;29"),
            (1800, 29.97, "00:01:00;02"),
            (17982, 29.97, "00:10:00;00"),
            (107892, 29.97, "01:00:00;00"),
            (3600, 59.94, "00:01:00;04"),
        ]

        for frame, rate, expected in cases:
            with self.subTest(frame=frame, rate=rate):
                # Act
                timecode = frames_to_timecode(frame, rate, drop_frame=True)

                # Assert
                self.assertEqual(expected, timecode)

    def test_given_a_drop_frame_flag_on_a_non_ntsc_rate_when_converting_then_uses_non_drop(self):
        # Act
        timecode = frames_to_timecode(25, 25.0, drop_frame=True)

        # Assert
        self.assertEqual("00:00:01:00", timecode)

    def test_given_resolve_frame_rate_settings_when_parsing_then_returns_the_rate(self):
        cases = [("24", 24.0), ("23.976", 23.976), ("29.97 DF", 29.97)]

        for setting, expected in cases:
            with self.subTest(setting=setting):
                # Act & Assert
                self.assertAlmostEqual(expected, parse_frame_rate(setting))

    def test_given_an_unreadable_frame_rate_when_parsing_then_raises(self):
        for setting in ("", "abc", "0", None):
            with self.subTest(setting=setting):
                # Act & Assert
                with self.assertRaises(ValueError):
                    parse_frame_rate(setting)
