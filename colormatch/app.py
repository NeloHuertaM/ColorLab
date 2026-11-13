"""Entry point used by the script installed in Resolve's Workspace > Scripts menu."""

from functools import partial

from colormatch import ui_fusion, ui_tk
from colormatch.engine import MatchError
from colormatch.form import format_results, options_from_form
from colormatch.imageio import ImageFormatError
from colormatch.workflow import WorkflowError, run

NO_INTERFACE_MESSAGE = (
    "Color Match: no hay interfaz disponible. UIManager está desactivado en esta versión de Resolve y "
    "tkinter no está instalado en el Python que usa Resolve. Usa la línea de comandos (python -m colormatch)."
)


def run_from_form(resolve, values, report=None):
    try:
        results = run(resolve, options_from_form(values), report)
    except (WorkflowError, MatchError, ImageFormatError, OSError, ValueError) as error:
        return "Error: %s" % error

    return format_results(results)


def launch(resolve, fusion_app=None, bmd_module=None, report=print):
    on_run = partial(run_from_form, resolve)

    if ui_fusion.is_available(fusion_app, bmd_module) and _show_fusion(fusion_app, bmd_module, on_run, report):
        return

    if ui_tk.is_available():
        ui_tk.show(on_run)

        return

    report(NO_INTERFACE_MESSAGE)


def _show_fusion(fusion_app, bmd_module, on_run, report):
    """Resolve proxies raise untyped errors when UIManager is locked, so any failure falls back to tkinter."""
    try:
        ui_fusion.show(fusion_app, bmd_module, on_run)
    except Exception as error:  # noqa: BLE001
        report("UIManager no disponible (%s); se usa la ventana alternativa." % error)

        return False

    return True
