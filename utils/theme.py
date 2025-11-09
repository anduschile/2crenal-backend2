"""Theme helpers for the Centro Renal SPA dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

PALETTE = {
    "primary": "#0f172a",
    "accent": "#0ea5e9",
    "background": "#f8fafc",
    "card": "#ffffff",
    "text": "#0f172a",
}

SEMAPHORE_COLORS = {
    "green": "#22c55e",
    "yellow": "#f59e0b",
    "red": "#ef4444",
}


@dataclass
class Thresholds:
    verde: float
    amarillo: float


def color_for(metric: str, value: float, thresholds: Dict[str, Dict[str, float]]) -> str:
    """Return a hex color for the metric based on configured thresholds."""
    if metric not in thresholds or value is None:
        return SEMAPHORE_COLORS["green"]

    th = thresholds[metric]
    amarillo = th.get("amarillo", th.get("yellow", 0))
    rojo = th.get("rojo", th.get("red", amarillo * 1.5 if amarillo else 1))

    if value <= th.get("verde", th.get("green", amarillo)):
        return SEMAPHORE_COLORS["green"]
    if value <= amarillo:
        return SEMAPHORE_COLORS["yellow"]
    if value <= rojo:
        return SEMAPHORE_COLORS["red"]
    return SEMAPHORE_COLORS["red"]


def badge_class(estado: str) -> str:
    """Return css class for estado badge."""
    estado = (estado or "").lower()
    if estado == "aprobado":
        return "badge badge-success"
    if estado == "pendiente":
        return "badge badge-warning"
    return "badge badge-danger"
