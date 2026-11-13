"""Window built with Resolve's UIManager (Studio, or free versions before 19.1)."""

from colormatch.form import CLIP_COLOURS, METHODS, MODES, PERCENT, default_values, preset_values

WINDOW_ID = "ColorMatchWindow"
_WINDOW_GEOMETRY = [200, 120, 520, 640]
_MAX_TRACK = 99
_MAX_NODE = 99


def is_available(fusion_app, bmd_module):
    try:
        return bool(fusion_app and bmd_module and fusion_app.UIManager)
    except AttributeError:
        return False


def show(fusion_app, bmd_module, on_run):
    ui = fusion_app.UIManager
    dispatcher = bmd_module.UIDispatcher(ui)
    window = dispatcher.AddWindow(
        {"ID": WINDOW_ID, "WindowTitle": "Color Match", "Geometry": _WINDOW_GEOMETRY},
        _layout(ui),
    )
    items = window.GetItems()
    _fill(items, default_values())
    handlers = _Handlers(fusion_app, dispatcher, items, on_run)
    getattr(window.On, WINDOW_ID).Close = handlers.close
    window.On.Close.Clicked = handlers.close
    window.On.Run.Clicked = handlers.run
    window.On.Browse.Clicked = handlers.browse
    window.On.Mode.CurrentIndexChanged = handlers.mode_changed
    window.Show()
    dispatcher.RunLoop()
    window.Hide()


class _Handlers:
    def __init__(self, fusion_app, dispatcher, items, on_run):
        self.fusion_app = fusion_app
        self.dispatcher = dispatcher
        self.items = items
        self.on_run = on_run

    def close(self, event):
        self.dispatcher.ExitLoop()

    def browse(self, event):
        path = self.fusion_app.RequestFile()

        if path:
            self.items["ReferenceImage"].Text = str(path)

    def mode_changed(self, event):
        preset = preset_values(self.items["Mode"].CurrentIndex)
        self.items["Method"].CurrentIndex = preset["method_index"]
        self.items["Skin"].Value = preset["skin"]
        self.items["Highlights"].Value = preset["highlights"]

    def run(self, event):
        self.items["Log"].PlainText = "Trabajando..."
        self.items["Log"].PlainText = self.on_run(_read(self.items), self._append)

    def _append(self, message):
        self.items["Log"].PlainText = self.items["Log"].PlainText + "\n" + message


def _layout(ui):
    return ui.VGroup(
        {"Spacing": 6},
        [
            ui.Label({"Text": "Modo", "Weight": 0}),
            ui.ComboBox({"ID": "Mode", "Weight": 0}),
            ui.Label({"Text": "Imagen de referencia (solo para transferir look)", "Weight": 0}),
            ui.HGroup(
                {"Weight": 0},
                [ui.LineEdit({"ID": "ReferenceImage"}), ui.Button({"ID": "Browse", "Text": "...", "Weight": 0})],
            ),
            ui.Label({"Text": "Método", "Weight": 0}),
            ui.ComboBox({"ID": "Method", "Weight": 0}),
            ui.HGroup(
                {"Weight": 0},
                [
                    ui.Label({"Text": "Pista de vídeo"}),
                    ui.SpinBox({"ID": "Track", "Minimum": 1, "Maximum": _MAX_TRACK}),
                    ui.Label({"Text": "Nodo (0 = último)"}),
                    ui.SpinBox({"ID": "Node", "Minimum": 0, "Maximum": _MAX_NODE}),
                ],
            ),
            ui.Label({"Text": "Solo planos con color de clip", "Weight": 0}),
            ui.ComboBox({"ID": "ClipColour", "Weight": 0}),
            _slider_row(ui, "Strength", "Intensidad"),
            _slider_row(ui, "Skin", "Proteger tonos de piel"),
            _slider_row(ui, "Highlights", "Proteger altas luces"),
            ui.Label({"Text": "Carpeta de LUTs", "Weight": 0}),
            ui.LineEdit({"ID": "LutFolder", "Weight": 0}),
            ui.HGroup(
                {"Weight": 0},
                [ui.Button({"ID": "Run", "Text": "Graduar planos"}), ui.Button({"ID": "Close", "Text": "Cerrar"})],
            ),
            ui.TextEdit({"ID": "Log", "ReadOnly": True}),
        ],
    )


def _slider_row(ui, item_id, label):
    return ui.HGroup(
        {"Weight": 0},
        [
            ui.Label({"Text": label, "MinimumSize": [170, 0]}),
            ui.Slider({"ID": item_id, "Minimum": 0, "Maximum": PERCENT, "Orientation": "Horizontal"}),
        ],
    )


def _fill(items, values):
    items["Mode"].AddItems([label for _, label in MODES])
    items["Method"].AddItems([label for _, label in METHODS])
    items["ClipColour"].AddItems([label for _, label in CLIP_COLOURS])
    items["Mode"].CurrentIndex = values["mode_index"]
    items["Method"].CurrentIndex = values["method_index"]
    items["ClipColour"].CurrentIndex = values["clip_colour_index"]
    items["ReferenceImage"].Text = values["reference_image"]
    items["Track"].Value = values["track"]
    items["Node"].Value = values["node"]
    items["Strength"].Value = values["strength"]
    items["Skin"].Value = values["skin"]
    items["Highlights"].Value = values["highlights"]
    items["LutFolder"].Text = values["lut_folder"]


def _read(items):
    return {
        "mode_index": items["Mode"].CurrentIndex,
        "reference_image": items["ReferenceImage"].Text,
        "method_index": items["Method"].CurrentIndex,
        "track": items["Track"].Value,
        "clip_colour_index": items["ClipColour"].CurrentIndex,
        "node": items["Node"].Value,
        "strength": items["Strength"].Value,
        "skin": items["Skin"].Value,
        "highlights": items["Highlights"].Value,
        "lut_folder": items["LutFolder"].Text,
    }
