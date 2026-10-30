"""Shared helpers: time/frequency grid, verification check record."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import fft as sfft


@dataclass
class Check:
    """One verification check. kind = internal (code must pass) or external (literature/bench)."""
    model: str
    name: str
    passed: bool
    expected: str
    obtained: str
    kind: str = "internal"
    note: str = ""

    def as_row(self) -> dict:
        return dict(model=self.model, check=self.name, kind=self.kind, expected=self.expected,
                    obtained=self.obtained, result="pass" if self.passed else "FAIL", note=self.note)


@dataclass
class Grid:
    """Uniform grid in retarded time tau (0 = arrival of the sphere centre) and its rfft frequencies."""
    fs: float
    t_pre: float
    t_post: float
    n: int = field(init=False)
    n_pre: int = field(init=False)

    def __post_init__(self):
        n = int(round((self.t_pre + self.t_post) * self.fs))
        n = sfft.next_fast_len(n + (n % 2), real=True)
        self.n = n + (n % 2)
        self.n_pre = int(round(self.t_pre * self.fs))

    @property
    def t(self) -> np.ndarray:
        return (np.arange(self.n) - self.n_pre) / self.fs

    @property
    def f(self) -> np.ndarray:
        return sfft.rfftfreq(self.n, 1.0 / self.fs)

    @property
    def df(self) -> float:
        return self.fs / self.n

    def to_time(self, spec: np.ndarray) -> np.ndarray:
        """Spectrum (continuous-FT scaling, unit/Hz) to time signal on self.t."""
        x = sfft.irfft(spec, n=self.n) * self.fs
        return np.roll(x, self.n_pre)

    def to_freq(self, x: np.ndarray) -> np.ndarray:
        """Time signal on self.t to spectrum with continuous-FT scaling."""
        return sfft.rfft(np.roll(x, -self.n_pre)) / self.fs

    @classmethod
    def from_params(cls, P) -> "Grid":
        return cls(P.si("simulation.fs"), P.si("simulation.t_pre"), P.si("simulation.t_post"))


def db20(x, ref=None, floor=-200.0):
    x = np.abs(np.asarray(x)).astype(float)
    ref = np.max(x) if ref is None else ref
    with np.errstate(divide="ignore"):
        out = 20 * np.log10(np.maximum(x, 1e-300) / ref)
    return np.maximum(out, floor)


def envelope_duration(t: np.ndarray, x: np.ndarray, level_db: float = -20.0) -> float:
    """Duration between first and last time the analytic envelope exceeds level_db re its peak."""
    from scipy.signal import hilbert
    env = np.abs(hilbert(x))
    thr = env.max() * 10 ** (level_db / 20)
    idx = np.where(env >= thr)[0]
    return float(t[idx[-1]] - t[idx[0]]) if idx.size else 0.0
