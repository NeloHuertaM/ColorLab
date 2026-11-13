import os
import tempfile
import unittest

import numpy as np

from colormatch.lut import CubeFormatError, apply_lut, build_lut, lattice, read_cube, write_cube


class LutTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "test.cube")

    def tearDown(self):
        self.folder.cleanup()

    def test_given_a_33_point_table_when_writing_then_file_has_header_and_35937_rows(self):
        # Arrange
        table = build_lut(lambda rgb: rgb ** 0.8)

        # Act
        write_cube(self.path, table, "Prueba")

        # Assert
        with open(self.path, encoding="ascii") as handle:
            lines = handle.read().splitlines()
        self.assertEqual(['TITLE "Prueba"', "LUT_3D_SIZE 33"], lines[:2])
        self.assertEqual(["DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"], lines[2:4])
        self.assertEqual(35937, len(lines) - 4)

    def test_given_a_written_table_when_reading_it_back_then_values_round_trip(self):
        # Arrange
        table = build_lut(lambda rgb: rgb[:, ::-1] * 0.9)
        write_cube(self.path, table)

        # Act
        loaded = read_cube(self.path)

        # Assert
        np.testing.assert_allclose(loaded, table, atol=1e-6)

    def test_given_the_identity_lattice_when_writing_then_red_changes_fastest(self):
        # Arrange
        table = lattice(3)

        # Act
        write_cube(self.path, table)

        # Assert
        with open(self.path, encoding="ascii") as handle:
            data = handle.read().splitlines()[4:]
        self.assertEqual("0.500000 0.000000 0.000000", data[1])
        self.assertEqual("0.000000 0.500000 0.000000", data[3])
        self.assertEqual("0.000000 0.000000 0.500000", data[9])

    def test_given_the_identity_table_when_applying_then_returns_the_input(self):
        # Arrange
        image = np.random.default_rng(4).uniform(0.0, 1.0, size=(16, 16, 3))

        # Act
        result = apply_lut(image, lattice(17))

        # Assert
        np.testing.assert_allclose(result, image, atol=1e-12)

    def test_given_a_nonlinear_table_when_applying_at_lattice_points_then_returns_table_values_exactly(self):
        # Arrange
        table = build_lut(lambda rgb: np.sqrt(rgb), size=9)

        # Act
        result = apply_lut(lattice(9), table)

        # Assert
        np.testing.assert_allclose(result, table, atol=1e-12)

    def test_given_a_function_with_out_of_range_output_when_building_then_values_are_clipped(self):
        # Arrange & Act
        table = build_lut(lambda rgb: rgb * 3.0 - 1.0, size=5)

        # Assert
        self.assertGreaterEqual(table.min(), 0.0)
        self.assertLessEqual(table.max(), 1.0)

    def test_given_a_file_with_missing_rows_when_reading_then_raises(self):
        # Arrange
        with open(self.path, "w", encoding="ascii") as handle:
            handle.write("LUT_3D_SIZE 2\n0 0 0\n1 1 1\n")

        # Act & Assert
        with self.assertRaises(CubeFormatError):
            read_cube(self.path)

    def test_given_a_file_without_size_when_reading_then_raises(self):
        # Arrange
        with open(self.path, "w", encoding="ascii") as handle:
            handle.write("0 0 0\n")

        # Act & Assert
        with self.assertRaises(CubeFormatError):
            read_cube(self.path)

    def test_given_a_1d_lut_when_reading_then_raises(self):
        # Arrange
        with open(self.path, "w", encoding="ascii") as handle:
            handle.write("LUT_1D_SIZE 2\n0 0 0\n1 1 1\n")

        # Act & Assert
        with self.assertRaises(CubeFormatError):
            read_cube(self.path)

    def test_given_an_invalid_size_when_building_then_raises(self):
        # Act & Assert
        with self.assertRaises(CubeFormatError):
            build_lut(lambda rgb: rgb, size=1)
