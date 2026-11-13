"""Drives DaVinci Resolve through its scripting API.

Every Resolve object is received as a parameter, so the whole flow can be
exercised with fakes outside Resolve.
"""

import os
import re
import tempfile
import time
from dataclasses import dataclass, field

from colormatch.engine import MODE_LOOK_TRANSFER, MODE_SHOT_MATCH, PRESETS, MatchError, MatchSettings, fit_correction
from colormatch.imageio import ImageFormatError, load_image
from colormatch.lut import write_cube
from colormatch.paths import default_lut_folder
from colormatch.timecode import frames_to_timecode, parse_frame_rate

LAST_NODE = 0
ALL_CLIP_COLOURS = ""
_STILL_EXTENSION = ".png"
_UNSAFE_FILE_CHARACTERS = re.compile(r"[^A-Za-z0-9_.-]+")
_MAX_NAME_LENGTH = 40


class WorkflowError(RuntimeError):
    pass


@dataclass
class WorkflowOptions:
    mode: str = MODE_SHOT_MATCH
    reference_image: str = ""
    track_index: int = 1
    clip_colour: str = ALL_CLIP_COLOURS
    node_index: int = LAST_NODE
    lut_folder: str = field(default_factory=default_lut_folder)
    still_folder: str = field(default_factory=lambda: os.path.join(tempfile.gettempdir(), "colormatch-stills"))
    settings: MatchSettings = field(default_factory=lambda: PRESETS[MODE_SHOT_MATCH])


@dataclass
class ClipResult:
    name: str
    applied: bool
    message: str
    lut_path: str = ""


@dataclass
class _PreparedClip:
    item: object
    graph: object
    node: int
    name: str
    lut_path: str


def run(resolve, options, report=None):
    """Grades the target clips and returns one ClipResult per clip."""
    report = report or (lambda message: None)
    project = _current_project(resolve)
    timeline = project.GetCurrentTimeline()

    if not timeline:
        raise WorkflowError("No hay ninguna línea de tiempo abierta.")

    resolve.OpenPage("color")
    original_timecode = timeline.GetCurrentTimecode()
    os.makedirs(options.lut_folder, exist_ok=True)
    os.makedirs(options.still_folder, exist_ok=True)

    try:
        reference_rgb, reference_id = _load_reference(project, timeline, options)
        targets = select_targets(timeline, options.track_index, options.clip_colour, reference_id)

        if not targets:
            raise WorkflowError("No hay planos de destino en la pista V%d con ese filtro." % options.track_index)

        report("Analizando %d planos..." % len(targets))
        prepared, results = _prepare_clips(project, timeline, targets, reference_rgb, options, report)
    finally:
        timeline.SetCurrentTimecode(original_timecode)

    if prepared:
        project.RefreshLUTList()

    results.extend(_apply_lut(clip) for clip in prepared)

    return results


def select_targets(timeline, track_index, clip_colour, excluded_id):
    items = timeline.GetItemListInTrack("video", track_index) or []
    wanted_colour = clip_colour.strip().lower()

    return [
        item
        for item in items
        if item.GetUniqueId() != excluded_id
        and (not wanted_colour or (item.GetClipColor() or "").lower() == wanted_colour)
    ]


def resolve_node_index(graph, requested):
    node_count = graph.GetNumNodes() or 1

    if requested == LAST_NODE or requested > node_count:
        return node_count

    return max(1, requested)


def node_graph(item):
    try:
        graph = item.GetNodeGraph()
    except (AttributeError, TypeError):
        graph = None

    return graph or item


def lut_file_name(timeline_name, position, clip_name, run_stamp):
    safe_timeline = _safe_name(timeline_name)
    safe_clip = _safe_name(clip_name)

    return "%s_%03d_%s_%s.cube" % (safe_timeline, position, safe_clip, run_stamp)


def _current_project(resolve):
    if not resolve:
        raise WorkflowError("No se pudo conectar con DaVinci Resolve.")

    project = resolve.GetProjectManager().GetCurrentProject()

    if not project:
        raise WorkflowError("No hay ningún proyecto abierto.")

    return project


def _load_reference(project, timeline, options):
    if options.mode == MODE_LOOK_TRANSFER:
        if not options.reference_image or not os.path.isfile(options.reference_image):
            raise WorkflowError("Elige una imagen de referencia que exista.")

        return load_image(options.reference_image), None

    item = timeline.GetCurrentVideoItem()

    if not item:
        raise WorkflowError("Coloca el cursor sobre el plano de referencia antes de ejecutar.")

    still_path = os.path.join(options.still_folder, "reference" + _STILL_EXTENSION)

    return _export_still(project, still_path), item.GetUniqueId()


def _prepare_clips(project, timeline, targets, reference_rgb, options, report):
    frame_rate = parse_frame_rate(timeline.GetSetting("timelineFrameRate"))
    drop_frame = str(timeline.GetSetting("timelineDropFrameTimecode")) == "1"
    run_stamp = time.strftime("%Y%m%d-%H%M%S")
    prepared = []
    failures = []

    for position, item in enumerate(targets, start=1):
        name = item.GetName() or "plano %d" % position
        report("[%d/%d] %s" % (position, len(targets), name))
        lut_path = os.path.join(
            options.lut_folder, lut_file_name(timeline.GetName(), position, name, run_stamp)
        )
        middle_frame = item.GetStart() + item.GetDuration() // 2
        timecode = frames_to_timecode(middle_frame, frame_rate, drop_frame)

        try:
            clip = _grade_clip(project, timeline, item, name, timecode, reference_rgb, options, lut_path)
        except (MatchError, ImageFormatError, WorkflowError, OSError) as error:
            failures.append(ClipResult(name, False, str(error)))
            continue

        prepared.append(clip)

    return prepared, failures


def _grade_clip(project, timeline, item, name, timecode, reference_rgb, options, lut_path):
    graph = node_graph(item)
    node = resolve_node_index(graph, options.node_index)

    if not timeline.SetCurrentTimecode(timecode):
        raise WorkflowError("No se pudo mover el cursor a %s." % timecode)

    still_path = os.path.join(options.still_folder, "target" + _STILL_EXTENSION)
    disabled = _set_node_enabled(graph, node, False)

    try:
        source_rgb = _export_still(project, still_path)
    finally:
        if disabled:
            _set_node_enabled(graph, node, True)

    correction = fit_correction(source_rgb, reference_rgb, options.settings)
    write_cube(lut_path, correction.to_lut(), "Colour match %s" % name)

    return _PreparedClip(item, graph, node, name, lut_path)


def _apply_lut(clip):
    if clip.graph.SetLUT(clip.node, clip.lut_path):
        return ClipResult(clip.name, True, "LUT aplicada en el nodo %d." % clip.node, clip.lut_path)

    return ClipResult(
        clip.name,
        False,
        "Resolve no aceptó la LUT en el nodo %d. Comprueba que la carpeta de LUTs está en las rutas de LUT de Resolve."
        % clip.node,
        clip.lut_path,
    )


def _set_node_enabled(graph, node, enabled):
    """Older Resolve versions have no SetNodeEnabled; the match then sees the node as it is."""
    try:
        return bool(graph.SetNodeEnabled(node, enabled))
    except (AttributeError, TypeError):
        return False


def _export_still(project, still_path):
    if os.path.exists(still_path):
        os.remove(still_path)

    if not project.ExportCurrentFrameAsStill(still_path) or not os.path.isfile(still_path):
        raise WorkflowError("Resolve no pudo exportar el fotograma actual. Abre la página Color e inténtalo de nuevo.")

    return load_image(still_path)


def _safe_name(text):
    cleaned = _UNSAFE_FILE_CHARACTERS.sub("_", str(text or "")).strip("_")

    return (cleaned or "clip")[:_MAX_NAME_LENGTH]
