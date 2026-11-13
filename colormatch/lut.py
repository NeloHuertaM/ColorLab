"""3D LUT lattice, .cube reading and writing, and trilinear application.

Tables are stored as an (size**3, 3) array in .cube order: red changes
fastest, then green, then blue.
"""

import numpy as np

DEFAULT_LUT_SIZE = 33
_MIN_LUT_SIZE = 2
_MAX_LUT_SIZE = 256


class CubeFormatError(ValueError):
    pass


def lattice(size=DEFAULT_LUT_SIZE):
    _validate_size(size)
    steps = np.linspace(0.0, 1.0, size)
    blue, green, red = np.meshgrid(steps, steps, steps, indexing="ij")

    return np.stack([red.ravel(), green.ravel(), blue.ravel()], axis=-1)


def build_lut(rgb_function, size=DEFAULT_LUT_SIZE):
    table = np.asarray(rgb_function(lattice(size)), dtype=np.float64)

    return np.clip(table, 0.0, 1.0)


def write_cube(path, table, title="Colour match"):
    size = _size_of(table)
    lines = [
        'TITLE "%s"' % title.replace('"', "'"),
        "LUT_3D_SIZE %d" % size,
        "DOMAIN_MIN 0.0 0.0 0.0",
        "DOMAIN_MAX 1.0 1.0 1.0",
    ]
    lines.extend("%.6f %.6f %.6f" % (red, green, blue) for red, green, blue in table)

    with open(path, "w", encoding="ascii", newline="\n") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def read_cube(path):
    size = None
    domain_min = np.zeros(3)
    domain_max = np.ones(3)
    rows = []

    with open(path, "r", encoding="ascii") as handle:
        for raw_line in handle:
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            keyword = line.split()[0]

            if keyword == "TITLE":
                continue

            if keyword == "LUT_3D_SIZE":
                size = int(line.split()[1])
            elif keyword == "DOMAIN_MIN":
                domain_min = np.array([float(value) for value in line.split()[1:4]])
            elif keyword == "DOMAIN_MAX":
                domain_max = np.array([float(value) for value in line.split()[1:4]])
            elif keyword == "LUT_1D_SIZE":
                raise CubeFormatError("No se admiten LUTs 1D.")
            else:
                rows.append([float(value) for value in line.split()])

    return _validated_table(size, rows, domain_min, domain_max)


def apply_lut(rgb, table):
    """Applies a LUT to RGB values in [0, 1] with trilinear interpolation."""
    size = _size_of(table)
    shape = np.shape(rgb)
    coordinates = np.clip(np.asarray(rgb, dtype=np.float64).reshape(-1, 3), 0.0, 1.0) * (size - 1)
    lower = np.minimum(np.floor(coordinates).astype(np.int64), size - 2)
    fraction = coordinates - lower
    result = np.zeros_like(coordinates)

    for corner in range(8):
        offset = np.array([(corner >> 0) & 1, (corner >> 1) & 1, (corner >> 2) & 1])
        index = lower + offset
        weights = np.prod(np.where(offset == 1, fraction, 1.0 - fraction), axis=1)
        flat = index[:, 0] + index[:, 1] * size + index[:, 2] * size * size
        result += weights[:, np.newaxis] * table[flat]

    return result.reshape(shape)


def _validated_table(size, rows, domain_min, domain_max):
    if size is None:
        raise CubeFormatError("Falta LUT_3D_SIZE.")

    _validate_size(size)

    if any(len(row) != 3 for row in rows):
        raise CubeFormatError("Cada línea de datos debe tener tres valores.")

    if len(rows) != size ** 3:
        raise CubeFormatError("Se esperaban %d líneas de datos y hay %d." % (size ** 3, len(rows)))

    if not np.allclose(domain_min, 0.0) or not np.allclose(domain_max, 1.0):
        raise CubeFormatError("Solo se admite el dominio [0, 1].")

    table = np.array(rows, dtype=np.float64)

    if not np.all(np.isfinite(table)):
        raise CubeFormatError("La LUT contiene valores no finitos.")

    return table


def _size_of(table):
    size = int(round(len(table) ** (1.0 / 3.0)))

    if size ** 3 != len(table) or np.shape(table)[1:] != (3,):
        raise CubeFormatError("La tabla no es una retícula RGB cúbica.")

    return size


def _validate_size(size):
    if not _MIN_LUT_SIZE <= size <= _MAX_LUT_SIZE:
        raise CubeFormatError("El tamaño de la LUT debe estar entre %d y %d." % (_MIN_LUT_SIZE, _MAX_LUT_SIZE))
