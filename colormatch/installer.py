"""Copies the Resolve script into the per-user Scripts folder."""

import argparse
import os
import sys

from colormatch.paths import default_lut_folder, user_scripts_folder

SCRIPT_NAME = "ColorMatch.py"
ENGINE_PLACEHOLDER = "__COLORMATCH_ENGINE_PATH__"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_TEMPLATE = os.path.join(PROJECT_ROOT, "resolve", SCRIPT_NAME)


def render_script(template_text, engine_path):
    if ENGINE_PLACEHOLDER not in template_text:
        raise ValueError("The script template has no engine path placeholder.")

    return template_text.replace(ENGINE_PLACEHOLDER, engine_path)


def install(target_folder, engine_path=PROJECT_ROOT, template_path=SCRIPT_TEMPLATE):
    with open(template_path, "r", encoding="utf-8") as handle:
        script = render_script(handle.read(), engine_path)

    os.makedirs(target_folder, exist_ok=True)
    destination = os.path.join(target_folder, SCRIPT_NAME)

    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(script)

    return destination


def uninstall(target_folder):
    destination = os.path.join(target_folder, SCRIPT_NAME)

    if os.path.isfile(destination):
        os.remove(destination)

        return True

    return False


def main(arguments=None):
    parser = argparse.ArgumentParser(description="Instala Color Match en el menú Workspace > Scripts de Resolve.")
    parser.add_argument("--target", default=user_scripts_folder(), help="Carpeta de scripts de Resolve.")
    parser.add_argument("--uninstall", action="store_true", help="Elimina el script instalado.")
    parsed = parser.parse_args(arguments)

    if parsed.uninstall:
        removed = uninstall(parsed.target)
        print("Script eliminado." if removed else "No había ningún script instalado en %s." % parsed.target)

        return 0

    destination = install(parsed.target)
    print("Script instalado en: %s" % destination)
    print("Motor: %s (Python %d.%d)" % (PROJECT_ROOT, sys.version_info[0], sys.version_info[1]))
    print("Las LUTs se escribirán por defecto en: %s" % default_lut_folder())

    return 0


if __name__ == "__main__":
    sys.exit(main())
