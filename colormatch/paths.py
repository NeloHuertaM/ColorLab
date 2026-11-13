"""Default locations Resolve uses on each operating system."""

import ntpath
import os
import posixpath
import sys

LUT_SUBFOLDER = "ColorMatch"
SCRIPT_CATEGORY = "Utility"


def master_lut_folder(platform=None, environment=None):
    platform = platform or sys.platform
    environment = os.environ if environment is None else environment

    if platform.startswith("win"):
        program_data = environment.get("PROGRAMDATA", r"C:\ProgramData")

        return ntpath.join(program_data, "Blackmagic Design", "DaVinci Resolve", "Support", "LUT")

    if platform == "darwin":
        return "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT"

    return "/opt/resolve/LUT"


def default_lut_folder(platform=None, environment=None):
    platform = platform or sys.platform

    return _path_module(platform).join(master_lut_folder(platform, environment), LUT_SUBFOLDER)


def user_scripts_folder(platform=None, environment=None):
    platform = platform or sys.platform
    environment = os.environ if environment is None else environment
    home = environment.get("HOME") or os.path.expanduser("~")

    if platform.startswith("win"):
        app_data = environment.get("APPDATA") or ntpath.join(home, "AppData", "Roaming")
        base = ntpath.join(app_data, "Blackmagic Design", "DaVinci Resolve", "Support", "Fusion", "Scripts")
    elif platform == "darwin":
        base = posixpath.join(
            home, "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts"
        )
    else:
        base = posixpath.join(home, ".local", "share", "DaVinciResolve", "Fusion", "Scripts")

    return _path_module(platform).join(base, SCRIPT_CATEGORY)


def _path_module(platform):
    return ntpath if platform.startswith("win") else posixpath
