import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from colormatch import imageio
from colormatch.imageio import ImageFormatError, analysis_view, load_image, save_png

try:
    from PIL import Image
except ImportError:
    Image = None


class ImageioTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.image = np.random.default_rng(6).uniform(0.0, 1.0, size=(23, 31, 3))

    def tearDown(self):
        self.folder.cleanup()

    def _path(self, name):
        return os.path.join(self.folder.name, name)

    def test_given_a_saved_png_when_loading_then_pixels_round_trip_within_8_bit_precision(self):
        # Arrange
        path = self._path("frame.png")
        save_png(path, self.image)

        # Act
        loaded = load_image(path)

        # Assert
        self.assertEqual((23, 31, 3), loaded.shape)
        np.testing.assert_allclose(loaded, self.image, atol=0.5 / 255 + 1e-6)

    def test_given_no_pillow_when_loading_a_saved_png_then_the_builtin_decoder_reads_it(self):
        # Arrange
        path = self._path("frame.png")
        save_png(path, self.image)

        # Act
        with mock.patch.object(imageio, "_pillow_available", return_value=False):
            loaded = load_image(path)

        # Assert
        np.testing.assert_allclose(loaded, self.image, atol=0.5 / 255 + 1e-6)

    @unittest.skipIf(Image is None, "Pillow is not installed")
    def test_given_pngs_with_adaptive_filters_when_decoding_without_pillow_then_matches_pillow(self):
        # Arrange
        gradient = np.linspace(0, 255, 64 * 48 * 3).reshape(48, 64, 3).astype(np.uint8)
        noisy = (gradient + np.random.default_rng(1).integers(0, 9, size=gradient.shape)).astype(np.uint8)
        rgba = np.concatenate([noisy, np.full((48, 64, 1), 255, dtype=np.uint8)], axis=2)
        cases = {
            "rgb.png": Image.fromarray(noisy, "RGB"),
            "rgba.png": Image.fromarray(rgba, "RGBA"),
            "grey16.png": Image.fromarray(noisy[..., 0].astype(np.uint16) * 257),
        }

        for name, picture in cases.items():
            with self.subTest(name=name):
                path = self._path(name)
                picture.save(path, optimize=True)

                # Act
                with mock.patch.object(imageio, "_pillow_available", return_value=False):
                    decoded = load_image(path)

                # Assert
                np.testing.assert_allclose(decoded, load_image(path), atol=1e-6)

    def test_given_a_16_bit_ppm_when_loading_without_pillow_then_returns_normalised_rgb(self):
        # Arrange
        path = self._path("frame.ppm")
        pixels = np.array([[[0, 32768, 65535]]], dtype=">u2")
        with open(path, "wb") as handle:
            handle.write(b"P6\n# comment\n1 1\n65535\n" + pixels.tobytes())

        # Act
        with mock.patch.object(imageio, "_pillow_available", return_value=False):
            loaded = load_image(path)

        # Assert
        np.testing.assert_allclose(loaded, [[[0.0, 32768 / 65535, 1.0]]], atol=1e-6)

    def test_given_a_large_frame_when_taking_the_analysis_view_then_longest_side_is_capped(self):
        # Arrange
        frame = np.zeros((1080, 1920, 3))

        # Act
        view = analysis_view(frame)

        # Assert
        self.assertLessEqual(max(view.shape[:2]), 512)

    def test_given_a_file_that_is_not_a_png_when_decoding_without_pillow_then_raises(self):
        # Arrange
        path = self._path("fake.png")
        with open(path, "wb") as handle:
            handle.write(b"not an image")

        # Act & Assert
        with mock.patch.object(imageio, "_pillow_available", return_value=False):
            with self.assertRaises(ImageFormatError):
                load_image(path)

    def test_given_a_tiff_without_pillow_when_loading_then_raises_with_a_hint(self):
        # Arrange
        path = self._path("frame.tif")

        # Act & Assert
        with mock.patch.object(imageio, "_pillow_available", return_value=False):
            with self.assertRaisesRegex(ImageFormatError, "Pillow"):
                load_image(path)
