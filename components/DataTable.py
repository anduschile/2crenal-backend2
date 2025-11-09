from __future__ import annotations

from typing import List, Optional

import pandas as pd
import streamlit as st

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

    HAS_AGGRID = True
except Exception:  # pragma: no cover
    HAS_AGGRID = False


def render_data_table(
    df: pd.DataFrame,
    height: int = 480,
    key: str = "datatable",
    pinned_columns: Optional[List[str]] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
):
    if df.empty:
        st.info("No hay datos para mostrar en la tabla.")
        return None

    wrapper = st.container()
    wrapper.markdown('<div class="table-card">', unsafe_allow_html=True)
    if title:
        wrapper.markdown(
            f"""
            <div class="table-card__header">
                <h3>{title}</h3>
                {'<p>' + description + '</p>' if description else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

    body = wrapper.container()
    body.markdown('<div class="table-card__body">', unsafe_allow_html=True)
    with body:
        if not HAS_AGGRID:
            st.dataframe(df, use_container_width=True, hide_index=True)
            grid = df
        else:
            builder = GridOptionsBuilder.from_dataframe(df)
            builder.configure_default_column(
                filter=True,
                sortable=True,
                resizable=True,
            )
            builder.configure_grid_options(
                rowHeight=44,
                enableRangeSelection=True,
                pagination=True,
                paginationPageSize=50,
                suppressAggFuncInHeader=True,
            )
            if pinned_columns:
                builder.configure_columns(pinned_columns, pinned="left")
            grid = AgGrid(
                df,
                gridOptions=builder.build(),
                height=height,
                fit_columns_on_grid_load=True,
                allow_unsafe_jscode=True,
                update_mode=GridUpdateMode.NO_UPDATE,
                enable_enterprise_modules=False,
                theme="streamlit",
                key=key,
            )
    body.markdown("</div>", unsafe_allow_html=True)
    wrapper.markdown("</div>", unsafe_allow_html=True)
    return grid
