"""Form fields shared by both user interfaces and their mapping to workflow options."""

from dataclasses import replace

from colormatch.engine import MODE_LOOK_TRANSFER, MODE_SHOT_MATCH, PRESETS
from colormatch.paths import default_lut_folder
from colormatch.workflow import ALL_CLIP_COLOURS, LAST_NODE, WorkflowOptions

PERCENT = 100
MODES = [
    (MODE_SHOT_MATCH, "Igualar planos al plano bajo el cursor"),
    (MODE_LOOK_TRANSFER, "Transferir el look de una imagen externa"),
]
METHODS = [
    ("mkl", "Lineal MKL (rápido y estable)"),
    ("sliced", "Transporte óptimo por cortes (más detalle)"),
    ("reinhard", "Reinhard (media y desviación)"),
]
CLIP_COLOURS = [
    (ALL_CLIP_COLOURS, "Todos los planos de la pista"),
    ("Orange", "Naranja"),
    ("Apricot", "Albaricoque"),
    ("Yellow", "Amarillo"),
    ("Lime", "Lima"),
    ("Olive", "Oliva"),
    ("Green", "Verde"),
    ("Teal", "Verde azulado"),
    ("Navy", "Azul marino"),
    ("Blue", "Azul"),
    ("Purple", "Morado"),
    ("Violet", "Violeta"),
    ("Pink", "Rosa"),
    ("Tan", "Canela"),
    ("Beige", "Beige"),
    ("Brown", "Marrón"),
    ("Chocolate", "Chocolate"),
]


def default_values():
    values = {
        "mode_index": 0,
        "reference_image": "",
        "track": 1,
        "clip_colour_index": 0,
        "node": LAST_NODE,
        "strength": PERCENT,
        "lut_folder": default_lut_folder(),
    }
    values.update(preset_values(0))

    return values


def preset_values(mode_index):
    settings = PRESETS[MODES[mode_index][0]]
    method_index = [key for key, _ in METHODS].index(settings.method)

    return {
        "method_index": method_index,
        "skin": int(round(settings.skin_protection * PERCENT)),
        "highlights": int(round(settings.highlight_protection * PERCENT)),
    }


def options_from_form(values):
    mode = MODES[int(values["mode_index"])][0]
    settings = replace(
        PRESETS[mode],
        method=METHODS[int(values["method_index"])][0],
        strength=float(values["strength"]) / PERCENT,
        skin_protection=float(values["skin"]) / PERCENT,
        highlight_protection=float(values["highlights"]) / PERCENT,
    )

    return WorkflowOptions(
        mode=mode,
        reference_image=str(values["reference_image"]).strip().strip('"'),
        track_index=max(1, int(values["track"])),
        clip_colour=CLIP_COLOURS[int(values["clip_colour_index"])][0],
        node_index=max(LAST_NODE, int(values["node"])),
        lut_folder=str(values["lut_folder"]).strip() or default_lut_folder(),
        settings=settings,
    )


def format_results(results):
    applied = sum(1 for result in results if result.applied)
    lines = ["%d de %d planos graduados." % (applied, len(results))]
    lines.extend("%s %s: %s" % ("OK " if result.applied else "ERR", result.name, result.message) for result in results)

    return "\n".join(lines)
