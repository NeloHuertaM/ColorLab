"""Image loading and saving.

Pillow is used when it is installed. Without it, PNG (8 or 16 bit,
non-interlaced) and binary PPM are decoded with numpy and zlib only, so the
Resolve script keeps working with nothing but numpy installed.
"""

import os
import struct
import zlib

import numpy as np

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}
_DEFAULT_ANALYSIS_SIDE = 512


class ImageFormatError(ValueError):
    pass


def load_image(path):
    """Returns the image as float32 RGB in [0, 1] with shape (height, width, 3)."""
    if _pillow_available():
        return _read_with_pillow(path)

    extension = os.path.splitext(path)[1].lower()

    if extension == ".png":
        return _read_png(path)

    if extension in (".ppm", ".pnm"):
        return _read_ppm(path)

    raise ImageFormatError(
        "Para leer '%s' hace falta Pillow. Usa PNG o instala Pillow." % os.path.basename(path)
    )


def _pillow_available():
    try:
        import PIL.Image  # noqa: F401
    except ImportError:
        return False

    return True


def save_png(path, rgb):
    """Writes float RGB in [0, 1] as an 8-bit PNG."""
    pixels = np.clip(np.round(np.asarray(rgb) * 255.0), 0, 255).astype(np.uint8)
    height, width = pixels.shape[:2]
    rows = np.concatenate([np.zeros((height, 1), dtype=np.uint8), pixels.reshape(height, width * 3)], axis=1)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    with open(path, "wb") as handle:
        handle.write(_PNG_SIGNATURE)
        handle.write(_png_chunk(b"IHDR", header))
        handle.write(_png_chunk(b"IDAT", zlib.compress(rows.tobytes(), 6)))
        handle.write(_png_chunk(b"IEND", b""))


def analysis_view(rgb, max_side=_DEFAULT_ANALYSIS_SIDE):
    """Subsamples a frame for statistics so every frame costs about the same."""
    height, width = rgb.shape[:2]
    step = max(1, int(np.ceil(max(height, width) / float(max_side))))

    return rgb[::step, ::step]


def _read_with_pillow(path):
    from PIL import Image

    with Image.open(path) as image:
        if image.mode in ("I;16", "I;16B", "I;16L", "I"):
            grey = np.asarray(image, dtype=np.float64) / 65535.0

            return _to_rgb(grey[..., np.newaxis]).astype(np.float32)

        rgb = np.asarray(image.convert("RGB"), dtype=np.float64) / 255.0

    return rgb.astype(np.float32)


def _read_png(path):
    with open(path, "rb") as handle:
        data = handle.read()

    if not data.startswith(_PNG_SIGNATURE):
        raise ImageFormatError("'%s' no es un archivo PNG." % os.path.basename(path))

    header, compressed = _png_chunks(data)
    width, height, bit_depth, colour_type, _, _, interlace = struct.unpack(">IIBBBBB", header)

    if colour_type not in _PNG_CHANNELS or bit_depth not in (8, 16) or interlace != 0:
        raise ImageFormatError("Sin Pillow solo se admite PNG de 8 o 16 bits no entrelazado.")

    channels = _PNG_CHANNELS[colour_type]
    bytes_per_pixel = channels * bit_depth // 8
    raw = np.frombuffer(zlib.decompress(compressed), dtype=np.uint8)
    rows = _png_unfilter(raw, height, width * bytes_per_pixel, bytes_per_pixel)

    if bit_depth == 16:
        samples = rows.view(">u2").astype(np.float64) / 65535.0
    else:
        samples = rows.astype(np.float64) / 255.0

    return _to_rgb(samples.reshape(height, width, channels)).astype(np.float32)


def _png_chunks(data):
    position = len(_PNG_SIGNATURE)
    header = None
    compressed = bytearray()

    while position < len(data):
        length, kind = struct.unpack(">I4s", data[position:position + 8])
        body = data[position + 8:position + 8 + length]
        position += 12 + length

        if kind == b"IHDR":
            header = body
        elif kind == b"IDAT":
            compressed.extend(body)
        elif kind == b"IEND":
            break

    if header is None:
        raise ImageFormatError("El PNG no tiene cabecera IHDR.")

    return header, bytes(compressed)


def _png_unfilter(raw, height, stride, bytes_per_pixel):
    rows = np.zeros((height, stride), dtype=np.uint8)
    previous = np.zeros(stride, dtype=np.int32)
    expected_length = height * (stride + 1)

    if raw.size < expected_length:
        raise ImageFormatError("Los datos del PNG están truncados.")

    for row_index in range(height):
        start = row_index * (stride + 1)
        filter_type = raw[start]
        line = raw[start + 1:start + 1 + stride].astype(np.int32)
        rows[row_index] = _png_unfilter_line(filter_type, line, previous, bytes_per_pixel)
        previous = rows[row_index].astype(np.int32)

    return rows


def _png_unfilter_line(filter_type, line, previous, bytes_per_pixel):
    if filter_type == 0:
        return line.astype(np.uint8)

    if filter_type == 1:
        pixels = line.reshape(-1, bytes_per_pixel)

        return (np.cumsum(pixels, axis=0) & 0xFF).astype(np.uint8).reshape(-1)

    if filter_type == 2:
        return ((line + previous) & 0xFF).astype(np.uint8)

    if filter_type not in (3, 4):
        raise ImageFormatError("Filtro PNG desconocido %d." % filter_type)

    filtered = line.tolist()
    above = previous.tolist()
    result = [0] * len(filtered)

    for index, value in enumerate(filtered):
        left = result[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        result[index] = (value + _png_predictor(filter_type, left, above, index, bytes_per_pixel)) & 0xFF

    return np.array(result, dtype=np.uint8)


def _png_predictor(filter_type, left, previous, index, bytes_per_pixel):
    if filter_type == 1:
        return left

    up = previous[index]

    if filter_type == 3:
        return (left + up) // 2

    upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
    estimate = left + up - upper_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_upper_left = abs(estimate - upper_left)

    if distance_left <= distance_up and distance_left <= distance_upper_left:
        return left

    if distance_up <= distance_upper_left:
        return up

    return upper_left


def _read_ppm(path):
    with open(path, "rb") as handle:
        data = handle.read()

    tokens = []
    position = 0

    while len(tokens) < 4:
        while data[position:position + 1].isspace():
            position += 1

        if data[position:position + 1] == b"#":
            position = data.index(b"\n", position) + 1
            continue

        end = position

        while not data[end:end + 1].isspace():
            end += 1

        tokens.append(data[position:end])
        position = end

    magic, width, height, max_value = tokens[0], int(tokens[1]), int(tokens[2]), int(tokens[3])

    if magic != b"P6":
        raise ImageFormatError("Solo se admite PPM binario (P6).")

    dtype = ">u2" if max_value > 255 else np.uint8
    pixels = np.frombuffer(data[position + 1:], dtype=dtype, count=width * height * 3)

    return (pixels.reshape(height, width, 3).astype(np.float64) / max_value).astype(np.float32)


def _to_rgb(samples):
    channels = samples.shape[-1]

    if channels in (1, 2):
        return np.repeat(samples[..., :1], 3, axis=-1)

    return samples[..., :3]


def _png_chunk(kind, body):
    checksum = zlib.crc32(kind + body) & 0xFFFFFFFF

    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", checksum)
