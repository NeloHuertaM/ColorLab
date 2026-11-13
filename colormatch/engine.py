"""High level matching: from two frames to a correction LUT."""

from dataclasses import dataclass, replace

import numpy as np

from colormatch.colorspace import oklab_to_rgb, rgb_to_oklab
from colormatch.imageio import analysis_view, load_image
from colormatch.lut import DEFAULT_LUT_SIZE, build_lut, write_cube
from colormatch.protection import protect
from colormatch.transfer import fit_transform

METHODS = ("reinhard", "mkl", "sliced")
MODE_SHOT_MATCH = "match"
MODE_LOOK_TRANSFER = "look"
_CLIPPED_BLACK = 0.02
_CLIPPED_WHITE = 0.995
_MIN_UNCLIPPED_SHARE = 0.25
_MIN_REFERENCE_LIGHTNESS_STD = 1e-3


class MatchError(ValueError):
    pass


@dataclass(frozen=True)
class MatchSettings:
    method: str = "mkl"
    strength: float = 1.0
    skin_protection: float = 0.0
    highlight_protection: float = 0.25
    sliced_iterations: int = 10
    lut_size: int = DEFAULT_LUT_SIZE
    seed: int = 7

    def validated(self):
        if self.method not in METHODS:
            raise MatchError("Método desconocido '%s'. Usa uno de: %s." % (self.method, ", ".join(METHODS)))

        return replace(
            self,
            strength=_unit(self.strength),
            skin_protection=_unit(self.skin_protection),
            highlight_protection=_unit(self.highlight_protection),
            sliced_iterations=max(1, int(self.sliced_iterations)),
        )


PRESETS = {
    MODE_SHOT_MATCH: MatchSettings(method="mkl", skin_protection=0.0, highlight_protection=0.25),
    MODE_LOOK_TRANSFER: MatchSettings(method="sliced", skin_protection=0.5, highlight_protection=0.5),
}


class ColourCorrection:
    """A fitted correction that maps display RGB to display RGB."""

    def __init__(self, transform, settings):
        self.transform = transform
        self.settings = settings

    def apply_oklab(self, oklab):
        transferred = self.transform.apply(oklab)
        protected = protect(oklab, transferred, self.settings.skin_protection, self.settings.highlight_protection)

        return oklab + self.settings.strength * (protected - oklab)

    def apply_rgb(self, rgb):
        shape = np.shape(rgb)
        oklab = rgb_to_oklab(np.asarray(rgb, dtype=np.float64).reshape(-1, 3))

        return np.clip(oklab_to_rgb(self.apply_oklab(oklab)), 0.0, 1.0).reshape(shape)

    def to_lut(self):
        return build_lut(self.apply_rgb, self.settings.lut_size)


def fit_correction(source_rgb, reference_rgb, settings=None):
    """Fits a correction that makes source_rgb look like reference_rgb."""
    settings = (settings or MatchSettings()).validated()
    source = _analysis_samples(source_rgb)
    reference = _analysis_samples(reference_rgb)

    if reference[:, 0].std() < _MIN_REFERENCE_LIGHTNESS_STD:
        raise MatchError("La referencia es plana (sin detalle tonal); no hay nada que igualar.")

    transform = fit_transform(settings.method, source, reference, settings.sliced_iterations, settings.seed)

    return ColourCorrection(transform, settings)


def match_files(source_path, reference_path, lut_path, settings=None, title="Colour match"):
    correction = fit_correction(load_image(source_path), load_image(reference_path), settings)
    write_cube(lut_path, correction.to_lut(), title)

    return correction


def _analysis_samples(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)

    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.size == 0:
        raise MatchError("Se esperaba una imagen RGB con forma (alto, ancho, 3).")

    if not np.all(np.isfinite(rgb)):
        raise MatchError("La imagen contiene valores no finitos.")

    samples = rgb_to_oklab(np.clip(analysis_view(rgb), 0.0, 1.0).reshape(-1, 3))
    unclipped = (samples[:, 0] > _CLIPPED_BLACK) & (samples[:, 0] < _CLIPPED_WHITE)

    if unclipped.mean() >= _MIN_UNCLIPPED_SHARE:
        return samples[unclipped]

    return samples


def _unit(value):
    return float(np.clip(value, 0.0, 1.0))
