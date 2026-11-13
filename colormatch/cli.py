"""Command line: build a matching LUT from two images without Resolve."""

import argparse
import sys
from dataclasses import replace

from colormatch.colorspace import mean_delta_e
from colormatch.engine import METHODS, MODE_LOOK_TRANSFER, MODE_SHOT_MATCH, PRESETS, MatchError, fit_correction
from colormatch.imageio import ImageFormatError, load_image, save_png
from colormatch.lut import CubeFormatError, write_cube


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m colormatch",
        description="Genera una LUT .cube que hace que SOURCE se parezca a REFERENCE.",
    )
    parser.add_argument("source", help="Fotograma a corregir (PNG, TIFF, JPG...).")
    parser.add_argument("reference", help="Fotograma o imagen de referencia.")
    parser.add_argument("output", help="Ruta de la LUT .cube de salida.")
    parser.add_argument("--mode", choices=(MODE_SHOT_MATCH, MODE_LOOK_TRANSFER), default=MODE_SHOT_MATCH)
    parser.add_argument("--method", choices=METHODS, help="Sustituye el método del modo elegido.")
    parser.add_argument("--strength", type=float, default=1.0, help="Intensidad entre 0 y 1.")
    parser.add_argument("--skin", type=float, help="Protección de piel entre 0 y 1.")
    parser.add_argument("--highlights", type=float, help="Protección de altas luces entre 0 y 1.")
    parser.add_argument("--size", type=int, default=33, help="Puntos por eje de la LUT.")
    parser.add_argument("--preview", help="Guarda SOURCE corregido como PNG para revisarlo.")

    return parser


def settings_from_arguments(parsed):
    settings = replace(PRESETS[parsed.mode], strength=parsed.strength, lut_size=parsed.size)

    if parsed.method:
        settings = replace(settings, method=parsed.method)

    if parsed.skin is not None:
        settings = replace(settings, skin_protection=parsed.skin)

    if parsed.highlights is not None:
        settings = replace(settings, highlight_protection=parsed.highlights)

    return settings


def main(arguments=None):
    parsed = build_parser().parse_args(arguments)

    try:
        source = load_image(parsed.source)
        reference = load_image(parsed.reference)
        correction = fit_correction(source, reference, settings_from_arguments(parsed))
        write_cube(parsed.output, correction.to_lut(), "Colour match")
    except (MatchError, ImageFormatError, CubeFormatError, OSError) as error:
        print("Error: %s" % error, file=sys.stderr)

        return 1

    corrected = correction.apply_rgb(source)
    print("LUT escrita en %s" % parsed.output)

    if parsed.mode == MODE_SHOT_MATCH and source.shape == reference.shape:
        print("Delta E 2000 medio: %.2f antes, %.2f después" % (mean_delta_e(source, reference), mean_delta_e(corrected, reference)))

    if parsed.preview:
        save_png(parsed.preview, corrected)
        print("Vista previa en %s" % parsed.preview)

    return 0
