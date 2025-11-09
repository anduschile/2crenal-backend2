from __future__ import annotations

from typing import Optional

import streamlit as st


def chart_container(title: str, description: Optional[str] = None):
    """Context manager that renders a chart frame with title."""
    st.markdown(
        f"""
        <div class="chart-card">
            <div class="chart-card__header">
                <div>
                    <h3>{title}</h3>
                    {"<p>" + description + "</p>" if description else ""}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return st.container()
