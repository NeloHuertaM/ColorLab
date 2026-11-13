"""Color Match for DaVinci Resolve (Workspace > Scripts > Utility > ColorMatch).

The installer replaces ENGINE_PATH with the folder that holds the colormatch
package. Set the COLORMATCH_HOME environment variable to override it.
"""

import os
import sys

ENGINE_PATH = r"__COLORMATCH_ENGINE_PATH__"


def _engine_path():
    return os.environ.get("COLORMATCH_HOME") or ENGINE_PATH


def _resolve_handle():
    if globals().get("resolve"):
        return globals()["resolve"]

    if globals().get("app"):
        return globals()["app"].GetResolve()

    if globals().get("bmd"):
        return globals()["bmd"].scriptapp("Resolve")

    try:
        import DaVinciResolveScript
    except ImportError:
        return None

    return DaVinciResolveScript.scriptapp("Resolve")


def _main():
    engine_path = _engine_path()

    if engine_path not in sys.path:
        sys.path.insert(0, engine_path)

    try:
        from colormatch.app import launch
    except ImportError as error:
        print("Color Match: no se encontró el motor en '%s' (%s). Vuelve a ejecutar install.py." % (engine_path, error))

        return

    launch(_resolve_handle(), globals().get("fusion") or globals().get("fu"), globals().get("bmd"))


_main()
