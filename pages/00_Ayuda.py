from __future__ import annotations

from pathlib import Path

import streamlit as st

from app import use_app_shell

HELP_PATH = Path(__file__).resolve().parent.parent / "templates" / "ayuda.md"


def main():
    use_app_shell("Ayuda", "Ayuda / Guía rápida", active_page="Ayuda", compact_sidebar=True)
    st.markdown(HELP_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
