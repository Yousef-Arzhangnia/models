"""Study registry. Each study is a function(P, run) executed inside a tracker Run."""
from __future__ import annotations

from typing import Callable

REGISTRY: dict[str, dict] = {}


def study(name: str, model: str, milestone: str, title: str):
    def deco(fn: Callable):
        REGISTRY[name] = dict(fn=fn, model=model, milestone=milestone, title=title)
        return fn
    return deco


def load_all() -> dict[str, dict]:
    from . import demo, m1  # noqa: F401  (registration side effects)
    return REGISTRY
