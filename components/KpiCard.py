from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Literal, Optional

import streamlit as st

PALETTE = {
    "primary": "#2563EB",
    "neutral": "#64748B",
    "success": "#16A34A",
    "warning": "#F97316",
    "danger": "#EF4444",
}


@dataclass
class KpiModel:
    label: str
    value: str
    note: Optional[str] = None
    tone: Literal["primary", "neutral", "success", "warning", "danger"] = "primary"
    delta: Optional[str] = None
    delta_tone: Literal["neutral", "success", "warning", "danger"] = "neutral"


def render_kpi_card(model: KpiModel) -> None:
    border_color = PALETTE.get(model.tone, PALETTE["primary"])
    note_text = model.note or ""
    delta = ""
    if model.delta:
        badge_color = PALETTE.get(model.delta_tone, PALETTE["neutral"])
        delta = f'<span class="badge" style="background: rgba(37,99,235,0.08); color: {badge_color};">{model.delta}</span>'
    html = dedent(
        f"""
        <div class="kpi-card" style="border-top: 4px solid {border_color};">
        <div class="kpi-label">{model.label}</div>
        <div class="kpi-value">{model.value}</div>
        <div class="kpi-foot">
        {delta}
        {f'<div class="kpi-note">{note_text}</div>' if note_text else ''}
        </div>
        </div>
        """
    )
    st.markdown(html, unsafe_allow_html=True)
