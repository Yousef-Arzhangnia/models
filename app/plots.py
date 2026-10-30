"""Plotly helpers with consistent styling and units."""
import plotly.graph_objects as go

PALETTE = {"today": "#B4532A", "upgrade1": "#1F5F8B", "a": "#2E7D5B", "b": "#7A4FA0", "grey": "#888888"}


def fig(title: str, x: str, y: str, height: int = 380, logx: bool = False, logy: bool = False):
    f = go.Figure()
    f.update_layout(title=dict(text=title, x=0, font=dict(size=14)), height=height,
                    xaxis_title=x, yaxis_title=y, margin=dict(l=60, r=20, t=50, b=50),
                    legend=dict(font=dict(size=10)), hovermode="x unified")
    if logx:
        f.update_xaxes(type="log")
    if logy:
        f.update_yaxes(type="log")
    return f


def vline(f, x, text="", color="#888888", dash="dot"):
    f.add_vline(x=x, line=dict(color=color, dash=dash, width=1), annotation_text=text,
                annotation_font_size=9, annotation_position="top")
