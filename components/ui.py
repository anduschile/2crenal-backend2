from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence

import streamlit as st


@dataclass
class NavItem:
    label: str
    icon: str
    slug: str


DEFAULT_NAV: Sequence[NavItem] = [
    NavItem("Dashboard", "&#128200;", "app"),
    NavItem("Registrar", "&#9998;", "Registro"),
    NavItem("Ayuda", "&#128712;", "Ayuda"),
    NavItem("Personas", "&#128101;", "Personas"),
    NavItem("Permisos", "&#128221;", "Permisos"),
    NavItem("Licencias", "&#128137;", "Licencias"),
    NavItem("Reportes", "&#128202;", "Reportes"),
    NavItem("Config", "&#9881;", "Config"),
]


@dataclass
class TopbarChip:
    label: str
    variant: str = "soft"
    icon: Optional[str] = None


def render_sidebar_nav(active_page: str, *, items: Sequence[NavItem] = DEFAULT_NAV) -> None:
    chips_html = []
    for item in items:
        active = str(item.slug == active_page).lower()
        href = "/" if item.slug == "app" else f"/{item.slug}"
        chips_html.append(
            f'<a class="nav-item" data-active="{active}" href="{href}" target="_self">'
            f'<span class="nav-icon">{item.icon}</span><span>{item.label}</span>'
            "</a>"
        )
    nav_markup = "".join(chips_html)
    st.markdown(
        f"""
        <div class="sidebar-shell">
            <div class="sidebar-brand">
                <div class="avatar">CR</div>
                <div>
                    <p class="eyebrow">Panel</p>
                    <h3>Centro Renal SPA</h3>
                </div>
            </div>
            <div class="sidebar-nav">{nav_markup}</div>
            <div class="sidebar-cta">
                <p>Última sincronización automática cada 09:00 hrs.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_topbar(
    title: str,
    subtitle: str,
    *,
    greeting: str = "Panel operativo",
    chips: Optional[Iterable[TopbarChip]] = None,
    actions: Optional[Callable[[], None]] = None,
) -> None:
    chips = list(chips or [])
    container = st.container()
    container.markdown('<div class="topbar">', unsafe_allow_html=True)
    left, right = container.columns([3, 2])
    with left:
        st.markdown(
            f"""
            <div class="identity">
                <p class="eyebrow">{greeting}</p>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if chips:
            pills = "".join(
                f'<span class="chip" data-variant="{chip.variant}">'
                f'{(chip.icon + " ") if chip.icon else ""}{chip.label}'
                "</span>"
                for chip in chips
            )
            st.markdown(f'<div class="chip-group">{pills}</div>', unsafe_allow_html=True)
    with right:
        actions_holder = st.container()
        with actions_holder:
            st.markdown('<div class="topbar-actions">', unsafe_allow_html=True)
            if actions:
                actions()
            st.markdown("</div>", unsafe_allow_html=True)
    container.markdown("</div>", unsafe_allow_html=True)


@contextmanager
def card(title: Optional[str] = None, description: Optional[str] = None, *, classes: str = ""):
    container = st.container()
    class_attr = f"panel-card {classes}".strip()
    container.markdown(f'<div class="{class_attr}">', unsafe_allow_html=True)
    if title:
        container.markdown(
            f"<div class='panel-card__header'><h3>{title}</h3>"
            f"{'<p>' + description + '</p>' if description else ''}</div>",
            unsafe_allow_html=True,
        )
    yield container
    container.markdown("</div>", unsafe_allow_html=True)
