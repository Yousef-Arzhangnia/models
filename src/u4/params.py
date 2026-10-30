"""Load params.yaml and convert values to SI.

Every leaf in params.yaml is a mapping with value, unit, tag and optional note and tbd.
`Params.si(path)` returns the value in SI units, `Params.get(path)` the full entry.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

from .paths import PARAMS_FILE

# Unit to SI factor. Units mapped to None are returned unchanged (dB, °C, strings, coefficient lists).
_UNITS: dict[str, float | None] = {
    "m": 1.0, "mm": 1e-3, "µm": 1e-6, "um": 1e-6, "nm": 1e-9,
    "s": 1.0, "ms": 1e-3, "µs": 1e-6, "us": 1e-6, "ns": 1e-9,
    "Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9, "MS/s": 1e6, "GS/s": 1e9,
    "J": 1.0, "µJ": 1e-6, "nJ": 1e-9, "J/cm²": 1e4,
    "m/s": 1.0, "kg/m³": 1.0, "Pa": 1.0, "kPa": 1e3, "MPa": 1e6,
    "V": 1.0, "mV": 1e-3, "µV/Pa": 1e-6, "V/Pa": 1.0, "nV/√Hz": 1e-9,
    "1/cm": 100.0, "1/m": 1.0, "mrad": 1e-3, "Ω": 1.0, "K": 1.0, "J/(kg K)": 1.0,
    "1": 1.0, "bit": 1.0, "count": 1.0, "LSB": 1.0,
    "dB": None, "°C": None, "-": None, "dB/(cm MHz²)": None, "dB/(cm MHz^n)": None,
    "m/s per °C^k": None, "dB/(km kHz²) per °C^k": None,
}


@dataclass
class Param:
    path: str
    value: Any
    unit: str
    tag: str
    note: str = ""
    tbd: bool = False

    @property
    def si(self) -> Any:
        return to_si(self.value, self.unit)

    def label(self) -> str:
        """Human label: value, unit and tag, e.g. '1.3 ns [S]'."""
        v = self.value
        if isinstance(v, list):
            v = " to ".join(f"{x:g}" if isinstance(x, (int, float)) else str(x) for x in v)
        elif isinstance(v, float):
            v = f"{v:g}"
        unit = "" if self.unit in ("-", "1") else f" {self.unit}"
        flag = " TBD" if self.tbd else ""
        return f"{v}{unit} {self.tag}{flag}"


def to_si(value: Any, unit: str) -> Any:
    if unit not in _UNITS:
        raise ValueError(f"Unknown unit '{unit}'. Add it to u4.params._UNITS.")
    f = _UNITS[unit]
    if f is None or value is None or isinstance(value, str):
        return value
    if isinstance(value, list):
        return [x * f for x in value]
    return value * f


def from_si(value: Any, unit: str) -> Any:
    f = _UNITS[unit]
    if f is None or value is None or isinstance(value, str):
        return value
    if isinstance(value, list):
        return [x / f for x in value]
    return value / f


def _is_leaf(node: Any) -> bool:
    return isinstance(node, dict) and "value" in node and "unit" in node and "tag" in node


class Params:
    """Read-only view on params.yaml with optional in-memory overrides (used by the pages)."""

    def __init__(self, raw: dict, source: Path | None = None):
        self.raw = raw
        self.source = source
        self._validate(raw, "")

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Params":
        p = Path(path) if path else PARAMS_FILE
        with open(p, encoding="utf-8") as fh:
            return cls(yaml.safe_load(fh), p)

    def _validate(self, node: Any, prefix: str) -> None:
        if _is_leaf(node):
            to_si(node["value"], node["unit"])  # raises on unknown unit
            if not str(node["tag"]).startswith("["):
                raise ValueError(f"{prefix}: tag must look like [S], [M], [C] or [L, ref]")
            return
        if not isinstance(node, dict):
            raise ValueError(f"{prefix}: expected a mapping with value/unit/tag")
        for k, v in node.items():
            self._validate(v, f"{prefix}.{k}" if prefix else k)

    def _node(self, path: str) -> dict:
        node: Any = self.raw
        for part in path.split("."):
            node = node[part]
        return node

    def get(self, path: str) -> Param:
        n = self._node(path)
        if not _is_leaf(n):
            raise KeyError(f"{path} is a group, not a parameter")
        return Param(path, n["value"], n["unit"], n["tag"], n.get("note", ""), bool(n.get("tbd", False)))

    def si(self, path: str) -> Any:
        return self.get(path).si

    def value(self, path: str) -> Any:
        return self.get(path).value

    def leaves(self) -> Iterator[Param]:
        def walk(node: Any, prefix: str):
            if _is_leaf(node):
                yield Param(prefix, node["value"], node["unit"], node["tag"], node.get("note", ""),
                            bool(node.get("tbd", False)))
                return
            for k, v in node.items():
                yield from walk(v, f"{prefix}.{k}" if prefix else k)
        yield from walk(self.raw, "")

    def tbd(self) -> list[Param]:
        return [p for p in self.leaves() if p.tbd]

    def with_overrides(self, overrides: dict[str, Any]) -> "Params":
        """Copy with some values replaced (values in the file's units, not SI)."""
        raw = copy.deepcopy(self.raw)
        for path, val in overrides.items():
            node: Any = raw
            parts = path.split(".")
            for part in parts[:-1]:
                node = node[part]
            node[parts[-1]]["value"] = val
        return Params(raw, self.source)


def load() -> Params:
    return Params.load()
