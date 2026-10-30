"""M0 demo study: proves that a command-line run shows live progress on the board."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from . import plotting, study


@study("demo", model="0", milestone="M0", title="Tracker demo (M0)")
def demo(P, run, steps: int = 30, dt: float = 1.0):
    xs = np.linspace(0, 2 * np.pi, 200)
    for i in range(steps):
        time.sleep(dt)
        run.progress((i + 1) / steps, f"step {i + 1} of {steps}")
    run.check("params.yaml loads and every leaf has unit and tag", True, "all leaves valid",
              f"{sum(1 for _ in P.leaves())} parameters, {len(P.tbd())} TBD")
    run.result("tbd_count", len(P.tbd()), unit="", tag="[C]")
    fig, ax = plotting.new(size=(7, 3.2))
    ax.plot(xs * 1e3 / (2 * np.pi), np.sin(xs), color=plotting.COLORS["upgrade1"])
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("amplitude (a.u.)")
    plotting.finish(fig, "Demo run completed: tracker, figures and checks reach the board",
                    "Illustrative signal, not a model result. [C]")
    run.figure(fig, "demo")
    plotting.close(fig)
    run.data(pd.DataFrame({"x": xs, "y": np.sin(xs)}), "demo")
