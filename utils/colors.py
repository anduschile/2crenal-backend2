"""Design palette helpers shared across the dashboard."""

from __future__ import annotations

from typing import Dict, List

PALETTE: Dict[str, str] = {
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "accent": "#22D3EE",
    "text": "#0F172A",
    "muted": "#64748B",
    "surface": "#F8FAFC",
    "card": "#FFFFFF",
    "success": "#16A34A",
    "warning": "#F97316",
    "danger": "#EF4444",
}

CHART_SEQUENCE: List[str] = [
    PALETTE["primary"],
    "#38BDF8",
    "#34D399",
    "#FBBF24",
    "#F472B6",
    "#A78BFA",
    "#FDA4AF",
    "#7DD3FC",
]


def with_alpha(hex_color: str, alpha: float) -> str:
    """Return the rgba representation of a hex color with variable transparency."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def semantic(tone: str) -> str:
    """Return semantic color by tone (success, warning, danger...)."""
    tone = (tone or "").lower()
    mapping = {
        "success": PALETTE["success"],
        "positive": PALETTE["success"],
        "warning": PALETTE["warning"],
        "pending": PALETTE["warning"],
        "danger": PALETTE["danger"],
        "error": PALETTE["danger"],
        "neutral": PALETTE["muted"],
    }
    return mapping.get(tone, PALETTE["primary"])


def plotly_layout(**overrides) -> Dict:
    """Base layout dict used by every Plotly chart."""
    layout = {
        "template": "plotly_white",
        "font": {"family": "Inter, 'Segoe UI', sans-serif", "color": PALETTE["text"]},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": dict(l=24, r=24, t=40, b=32),
        "xaxis": dict(
            showgrid=True,
            gridcolor=with_alpha(PALETTE["text"], 0.08),
            zeroline=False,
            linecolor=with_alpha(PALETTE["text"], 0.12),
        ),
        "yaxis": dict(
            showgrid=True,
            gridcolor=with_alpha(PALETTE["text"], 0.06),
            zeroline=False,
            linecolor=with_alpha(PALETTE["text"], 0.12),
        ),
        "legend": dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor=with_alpha(PALETTE["text"], 0.05),
            borderwidth=1,
        ),
        "hoverlabel": dict(
            bgcolor="#FFFFFF",
            bordercolor=with_alpha(PALETTE["primary"], 0.25),
            font=dict(color=PALETTE["text"]),
        ),
    }
    layout.update(overrides)
    return layout
