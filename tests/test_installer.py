import contextlib
import io
import os
import tempfile
import unittest

from colormatch.installer import ENGINE_PLACEHOLDER, SCRIPT_TEMPLATE, install, main, render_script, uninstall
from colormatch.paths import default_lut_folder, user_scripts_folder


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.folder.cleanup()

    def test_given_the_shipped_template_when_installing_then_the_script_points_at_the_engine(self):
        # Act
        destination = install(self.folder.name, engine_path=r"D:\motor")

        # Assert
        with open(destination, encoding="utf-8") as handle:
            script = handle.read()
        self.assertIn('ENGINE_PATH = r"D:\\motor"', script)
        self.assertNotIn(ENGINE_PLACEHOLDER, script)

    def test_given_the_installed_script_when_compiling_then_it_is_valid_python(self):
        # Arrange
        destination = install(self.folder.name, engine_path="/opt/colormatch")

        # Act & Assert
        with open(destination, encoding="utf-8") as handle:
            compile(handle.read(), destination, "exec")

    def test_given_an_installed_script_when_uninstalling_then_it_is_removed(self):
        # Arrange
        install(self.folder.name)

        # Act
        removed = uninstall(self.folder.name)

        # Assert
        self.assertTrue(removed)
        self.assertEqual([], os.listdir(self.folder.name))

    def test_given_nothing_installed_when_uninstalling_then_reports_false(self):
        # Act & Assert
        self.assertFalse(uninstall(self.folder.name))

    def test_given_a_template_without_placeholder_when_rendering_then_raises(self):
        # Act & Assert
        with self.assertRaises(ValueError):
            render_script("print('hola')", "/motor")

    def test_given_a_target_folder_when_running_main_then_installs_there(self):
        # Act
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main(["--target", self.folder.name])

        # Assert
        self.assertEqual(0, exit_code)
        self.assertEqual(["ColorMatch.py"], os.listdir(self.folder.name))
        self.assertTrue(os.path.isfile(SCRIPT_TEMPLATE))


class PathsTests(unittest.TestCase):
    def test_given_each_platform_when_resolving_the_user_scripts_folder_then_uses_resolve_locations(self):
        cases = [
            ("win32", {"APPDATA": r"C:\Users\x\AppData\Roaming"}, r"C:\Users\x\AppData\Roaming"),
            ("darwin", {"HOME": "/Users/x"}, "/Users/x/Library/Application Support"),
            ("linux", {"HOME": "/home/x"}, "/home/x/.local/share/DaVinciResolve"),
        ]

        for platform, environment, prefix in cases:
            with self.subTest(platform=platform):
                # Act
                folder = user_scripts_folder(platform, environment)

                # Assert
                self.assertTrue(folder.startswith(prefix))
                self.assertTrue(folder.replace("\\", "/").endswith("Fusion/Scripts/Utility"))

    def test_given_windows_when_resolving_the_lut_folder_then_uses_the_master_lut_folder(self):
        # Act
        folder = default_lut_folder("win32", {"PROGRAMDATA": r"C:\ProgramData"})

        # Assert
        self.assertEqual(r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\ColorMatch", folder)

    def test_given_macos_when_resolving_the_lut_folder_then_uses_forward_slashes(self):
        # Act
        folder = default_lut_folder("darwin", {})

        # Assert
        self.assertEqual("/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/ColorMatch", folder)
