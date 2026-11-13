"""Frame number to SMPTE timecode, including drop-frame rates."""

_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60
_DROP_FRAME_TEN_MINUTES = 10


def parse_frame_rate(setting):
    """Parses Resolve's timelineFrameRate setting, for example '23.976' or '29.97 DF'."""
    text = str(setting).strip().split()[0] if str(setting).strip() else ""

    try:
        rate = float(text)
    except ValueError as error:
        raise ValueError("Frecuencia de fotogramas no reconocida: '%s'." % setting) from error

    if rate <= 0:
        raise ValueError("Frecuencia de fotogramas no reconocida: '%s'." % setting)

    return rate


def frames_to_timecode(frame, frame_rate, drop_frame=False):
    nominal = int(round(frame_rate))
    frame = int(frame)

    if drop_frame and nominal in (30, 60):
        frame = _drop_frame_adjusted(frame, nominal)

    separator = ";" if drop_frame and nominal in (30, 60) else ":"
    frames_per_hour = nominal * _SECONDS_PER_MINUTE * _MINUTES_PER_HOUR
    hours, remainder = divmod(frame, frames_per_hour)
    minutes, remainder = divmod(remainder, nominal * _SECONDS_PER_MINUTE)
    seconds, frames = divmod(remainder, nominal)

    return "%02d:%02d:%02d%s%02d" % (hours % 24, minutes, seconds, separator, frames)


def _drop_frame_adjusted(frame, nominal):
    dropped_per_minute = nominal // 15
    frames_per_minute = nominal * _SECONDS_PER_MINUTE - dropped_per_minute
    frames_per_ten_minutes = frames_per_minute * _DROP_FRAME_TEN_MINUTES + dropped_per_minute
    ten_minute_blocks, remainder = divmod(frame, frames_per_ten_minutes)
    skipped = dropped_per_minute * (_DROP_FRAME_TEN_MINUTES - 1) * ten_minute_blocks

    if remainder > dropped_per_minute:
        skipped += dropped_per_minute * ((remainder - dropped_per_minute) // frames_per_minute)

    return frame + skipped
