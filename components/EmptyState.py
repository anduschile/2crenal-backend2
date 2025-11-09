from __future__ import annotations

import streamlit as st


def render_empty_state(title: str, description: str, action: str | None = None):
    action_html = f"<p>{action}</p>" if action else ""
    st.markdown(
        f"""
        <div class="empty-state" role="alert">
            <h3>{title}</h3>
            <p>{description}</p>
            {action_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
