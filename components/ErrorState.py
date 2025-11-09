from __future__ import annotations

import streamlit as st


def render_error_state(title: str, description: str, suggestion: str | None = None):
    suggestion_html = f"<p class='error-hint'>{suggestion}</p>" if suggestion else ""
    st.markdown(
        f"""
        <div class="error-state" role="alert">
            <strong>{title}</strong>
            <p>{description}</p>
            {suggestion_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
