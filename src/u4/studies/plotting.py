"""Matplotlib helpers for report figures: finding as title, axis units, caption with source tags."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLORS = {"today": "#B4532A", "upgrade1": "#1F5F8B", 7e-6: "#2E7D5B", 12e-6: "#7A4FA0",
          "ideal": "#444444", "gap": "#999999"}


def new(nrows=1, ncols=1, size=(9, 4.2)):
    fig, ax = plt.subplots(nrows, ncols, figsize=size, constrained_layout=False)
    return fig, ax


def finish(fig, title: str, caption: str):
    fig.suptitle(title, fontsize=11.5, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.09, 1, 0.94))
    fig.text(0.01, 0.01, caption, fontsize=7.8, color="#444444", ha="left", va="bottom", wrap=True)
    return fig


def close(fig):
    plt.close(fig)
