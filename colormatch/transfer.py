"""Statistical colour transfer in Oklab.

Every fitted transform is a plain function of the input colour, so it can be
evaluated on a LUT lattice as well as on pixels.
"""

import numpy as np

_STD_FLOOR = 1e-3
_COVARIANCE_FLOOR = 1e-6
_MIN_GAIN = 0.02
_MAX_GAIN = 5.0
_QUANTILE_COUNT = 33
_FLAT_AXIS_RANGE = 1e-4


class ReinhardTransform:
    """Matches the mean and standard deviation of each Oklab channel."""

    def __init__(self, source, reference):
        self.source_mean = source.mean(axis=0)
        self.reference_mean = reference.mean(axis=0)
        gain = (reference.std(axis=0) + _STD_FLOOR) / (source.std(axis=0) + _STD_FLOOR)
        self.gain = np.clip(gain, _MIN_GAIN, _MAX_GAIN)

    def apply(self, oklab):
        return (oklab - self.source_mean) * self.gain + self.reference_mean


class LinearTransform:
    """Monge-Kantorovich linear transfer: the optimal affine map between two Gaussians."""

    def __init__(self, source, reference):
        self.source_mean = source.mean(axis=0)
        self.reference_mean = reference.mean(axis=0)
        source_covariance = _regularised_covariance(source)
        reference_covariance = _regularised_covariance(reference)
        source_root = _symmetric_power(source_covariance, 0.5)
        source_inverse_root = _symmetric_power(source_covariance, -0.5)
        middle = _symmetric_power(source_root @ reference_covariance @ source_root, 0.5)
        matrix = source_inverse_root @ middle @ source_inverse_root
        self.matrix = _clamp_gains(matrix)

    def apply(self, oklab):
        return (oklab - self.source_mean) @ self.matrix.T + self.reference_mean


class SlicedTransform:
    """Linear transfer refined by sliced optimal transport on random 3D rotations.

    The linear step fixes exposure, white balance and contrast. The sliced
    steps then match the shape of the distributions (for example a split tone)
    that a single affine map cannot express.
    """

    def __init__(self, source, reference, iterations, seed):
        self.linear = LinearTransform(source, reference)
        self.steps = []
        random = np.random.default_rng(seed)
        current = self.linear.apply(source)
        levels = np.linspace(0.0, 1.0, _QUANTILE_COUNT)

        for _ in range(iterations):
            rotation = _random_rotation(random)
            source_quantiles = np.quantile(current @ rotation, levels, axis=0)
            reference_quantiles = np.quantile(reference @ rotation, levels, axis=0)
            step = (rotation, source_quantiles, reference_quantiles)
            self.steps.append(step)
            current = _apply_sliced_step(current, step)

    def apply(self, oklab):
        current = self.linear.apply(oklab)

        for step in self.steps:
            current = _apply_sliced_step(current, step)

        return current


def fit_transform(method, source, reference, iterations=10, seed=7):
    if method == "reinhard":
        return ReinhardTransform(source, reference)

    if method == "mkl":
        return LinearTransform(source, reference)

    if method == "sliced":
        return SlicedTransform(source, reference, iterations, seed)

    raise ValueError("Método de transferencia desconocido '%s'." % method)


def _regularised_covariance(samples):
    if samples.shape[0] < 2:
        return np.eye(3) * _COVARIANCE_FLOOR

    return np.cov(samples, rowvar=False) + np.eye(3) * _COVARIANCE_FLOOR


def _symmetric_power(matrix, exponent):
    eigenvalues, eigenvectors = np.linalg.eigh((matrix + matrix.T) / 2.0)
    eigenvalues = np.maximum(eigenvalues, _COVARIANCE_FLOOR)

    return (eigenvectors * eigenvalues ** exponent) @ eigenvectors.T


def _clamp_gains(matrix):
    eigenvalues, eigenvectors = np.linalg.eigh((matrix + matrix.T) / 2.0)
    eigenvalues = np.clip(eigenvalues, _MIN_GAIN, _MAX_GAIN)

    return (eigenvectors * eigenvalues) @ eigenvectors.T


def _random_rotation(random):
    orthonormal, upper = np.linalg.qr(random.normal(size=(3, 3)))

    return orthonormal * np.sign(np.diag(upper))


def _apply_sliced_step(oklab, step):
    rotation, source_quantiles, reference_quantiles = step
    projected = oklab @ rotation
    matched = np.empty_like(projected)

    for axis in range(projected.shape[1]):
        matched[:, axis] = _monotone_map(projected[:, axis], source_quantiles[:, axis], reference_quantiles[:, axis])

    return matched @ rotation.T


def _monotone_map(values, source_knots, reference_knots):
    """Piecewise linear quantile map with slope one beyond the sampled range."""
    if source_knots[-1] - source_knots[0] < _FLAT_AXIS_RANGE:
        return values + (reference_knots.mean() - source_knots.mean())

    source_knots = _strictly_increasing(source_knots)
    reference_knots = np.maximum.accumulate(reference_knots)
    mapped = np.interp(values, source_knots, reference_knots)
    below = values < source_knots[0]
    above = values > source_knots[-1]
    mapped[below] = values[below] + (reference_knots[0] - source_knots[0])
    mapped[above] = values[above] + (reference_knots[-1] - source_knots[-1])

    return mapped


def _strictly_increasing(knots):
    minimum_step = (knots[-1] - knots[0]) * 1e-6
    steps = np.maximum(np.diff(knots), minimum_step)

    return np.concatenate([knots[:1], knots[0] + np.cumsum(steps)])
