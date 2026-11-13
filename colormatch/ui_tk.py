"""Fallback window built with tkinter, for Resolve builds where UIManager is disabled."""

from colormatch.form import CLIP_COLOURS, METHODS, MODES, PERCENT, default_values, preset_values

_MAX_TRACK = 99
_MAX_NODE = 99
_PADDING = 4


def is_available():
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False

    return True


def show(on_run):
    import tkinter
    from tkinter import filedialog, ttk

    root = tkinter.Tk()
    root.title("Color Match")
    values = default_values()
    variables = {
        "mode": tkinter.StringVar(value=MODES[values["mode_index"]][1]),
        "reference_image": tkinter.StringVar(value=values["reference_image"]),
        "method": tkinter.StringVar(value=METHODS[values["method_index"]][1]),
        "track": tkinter.IntVar(value=values["track"]),
        "node": tkinter.IntVar(value=values["node"]),
        "clip_colour": tkinter.StringVar(value=CLIP_COLOURS[values["clip_colour_index"]][1]),
        "strength": tkinter.IntVar(value=values["strength"]),
        "skin": tkinter.IntVar(value=values["skin"]),
        "highlights": tkinter.IntVar(value=values["highlights"]),
        "lut_folder": tkinter.StringVar(value=values["lut_folder"]),
    }
    frame = ttk.Frame(root, padding=8)
    frame.grid(sticky="nsew")
    frame.columnconfigure(1, weight=1)

    mode_box = _combo(ttk, frame, 0, "Modo", variables["mode"], MODES)
    ttk.Label(frame, text="Imagen de referencia").grid(row=1, column=0, sticky="w", pady=_PADDING)
    ttk.Entry(frame, textvariable=variables["reference_image"]).grid(row=1, column=1, sticky="ew")
    ttk.Button(
        frame,
        text="...",
        width=3,
        command=lambda: variables["reference_image"].set(filedialog.askopenfilename() or variables["reference_image"].get()),
    ).grid(row=1, column=2)
    _combo(ttk, frame, 2, "Método", variables["method"], METHODS)
    _spin(tkinter, frame, 3, "Pista de vídeo", variables["track"], 1, _MAX_TRACK)
    _spin(tkinter, frame, 4, "Nodo (0 = último)", variables["node"], 0, _MAX_NODE)
    _combo(ttk, frame, 5, "Color de clip", variables["clip_colour"], CLIP_COLOURS)
    _scale(tkinter, frame, 6, "Intensidad", variables["strength"])
    _scale(tkinter, frame, 7, "Proteger piel", variables["skin"])
    _scale(tkinter, frame, 8, "Proteger altas luces", variables["highlights"])
    ttk.Label(frame, text="Carpeta de LUTs").grid(row=9, column=0, sticky="w", pady=_PADDING)
    ttk.Entry(frame, textvariable=variables["lut_folder"]).grid(row=9, column=1, columnspan=2, sticky="ew")
    log = tkinter.Text(frame, height=12, width=64)
    log.grid(row=11, column=0, columnspan=3, sticky="nsew")

    mode_box.bind("<<ComboboxSelected>>", lambda event: _apply_preset(variables))
    ttk.Button(frame, text="Graduar planos", command=lambda: _run(root, log, variables, on_run)).grid(
        row=10, column=0, columnspan=3, sticky="ew", pady=_PADDING
    )
    root.mainloop()


def _combo(ttk, frame, row, label, variable, choices):
    ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=_PADDING)
    box = ttk.Combobox(frame, textvariable=variable, values=[text for _, text in choices], state="readonly")
    box.grid(row=row, column=1, columnspan=2, sticky="ew")

    return box


def _spin(tkinter, frame, row, label, variable, minimum, maximum):
    tkinter.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=_PADDING)
    tkinter.Spinbox(frame, from_=minimum, to=maximum, textvariable=variable, width=6).grid(
        row=row, column=1, sticky="w"
    )


def _scale(tkinter, frame, row, label, variable):
    tkinter.Label(frame, text=label).grid(row=row, column=0, sticky="w")
    tkinter.Scale(frame, from_=0, to=PERCENT, orient="horizontal", variable=variable).grid(
        row=row, column=1, columnspan=2, sticky="ew"
    )


def _apply_preset(variables):
    preset = preset_values(_index_of(MODES, variables["mode"].get()))
    variables["method"].set(METHODS[preset["method_index"]][1])
    variables["skin"].set(preset["skin"])
    variables["highlights"].set(preset["highlights"])


def _run(root, log, variables, on_run):
    log.delete("1.0", "end")
    log.insert("end", "Trabajando...\n")
    root.update()
    text = on_run(_read(variables), lambda message: _append(root, log, message))
    log.delete("1.0", "end")
    log.insert("end", text)


def _append(root, log, message):
    log.insert("end", message + "\n")
    root.update()


def _read(variables):
    return {
        "mode_index": _index_of(MODES, variables["mode"].get()),
        "reference_image": variables["reference_image"].get(),
        "method_index": _index_of(METHODS, variables["method"].get()),
        "track": variables["track"].get(),
        "clip_colour_index": _index_of(CLIP_COLOURS, variables["clip_colour"].get()),
        "node": variables["node"].get(),
        "strength": variables["strength"].get(),
        "skin": variables["skin"].get(),
        "highlights": variables["highlights"].get(),
        "lut_folder": variables["lut_folder"].get(),
    }


def _index_of(choices, label):
    labels = [text for _, text in choices]

    return labels.index(label) if label in labels else 0
