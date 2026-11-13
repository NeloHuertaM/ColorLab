import contextlib
import io
import os
import tempfile
import unittest

from colormatch.app import run_from_form
from colormatch.cli import main
from colormatch.form import default_values
from colormatch.imageio import save_png
from colormatch.lut import read_cube
from tests import synthetic


class CliTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        reference = synthetic.scene()
        self.source_path = self._path("source.png")
        self.reference_path = self._path("reference.png")
        save_png(self.source_path, synthetic.graded(reference, white_balance=(1.2, 1.0, 0.8)))
        save_png(self.reference_path, reference)

    def tearDown(self):
        self.folder.cleanup()

    def _path(self, name):
        return os.path.join(self.folder.name, name)

    def test_given_two_frames_when_running_the_cli_then_writes_a_valid_lut_and_a_preview(self):
        # Arrange
        output = io.StringIO()

        # Act
        with contextlib.redirect_stdout(output):
            exit_code = main([self.source_path, self.reference_path, self._path("out.cube"), "--preview", self._path("p.png")])

        # Assert
        self.assertEqual(0, exit_code)
        self.assertEqual((35937, 3), read_cube(self._path("out.cube")).shape)
        self.assertTrue(os.path.isfile(self._path("p.png")))
        self.assertIn("Delta E 2000", output.getvalue())

    def test_given_a_missing_file_when_running_the_cli_then_exits_with_an_error(self):
        # Arrange
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            exit_code = main([self._path("missing.png"), self.reference_path, self._path("out.cube")])

        # Assert
        self.assertEqual(1, exit_code)
        self.assertIn("Error", errors.getvalue())

    def test_given_an_invalid_lut_size_when_running_the_cli_then_exits_with_an_error(self):
        # Arrange
        errors = io.StringIO()

        # Act
        with contextlib.redirect_stderr(errors):
            exit_code = main([self.source_path, self.reference_path, self._path("out.cube"), "--size", "1"])

        # Assert
        self.assertEqual(1, exit_code)

    def test_given_resolve_is_not_reachable_when_running_from_the_form_then_returns_an_error_message(self):
        # Act
        text = run_from_form(None, default_values())

        # Assert
        self.assertTrue(text.startswith("Error:"))
