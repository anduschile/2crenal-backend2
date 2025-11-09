"""Tablas maestras y subtotales."""

from __future__ import annotations

from typing import Iterable, List

import pandas as pd
import streamlit as st

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

    HAS_AGGRID = True
except Exception:  # pragma: no cover
    HAS_AGGRID = False


def subtotales_por(df: pd.DataFrame, group_cols: Iterable[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[*group_cols, "registros", "dias"])
    grouped = (
        df.groupby(list(group_cols))
        .agg(registros=("tipo_registro", "count"), dias=("dias", "sum"))
        .reset_index()
    )
    total = pd.DataFrame(
        {
            group_cols[0]: ["TOTAL"],
            **{col: [""] for col in list(group_cols[1:])},
            "registros": [grouped["registros"].sum()],
            "dias": [grouped["dias"].sum()],
        }
    )
    return pd.concat([grouped, total], ignore_index=True)


def render_master_table(df: pd.DataFrame, height: int = 420) -> None:
    if df.empty:
        st.info("No hay registros para los filtros seleccionados.")
        return
    if HAS_AGGRID:
        builder = GridOptionsBuilder.from_dataframe(df)
        builder.configure_default_column(
            filter=True,
            sortable=True,
            resizable=True,
            min_column_width=120,
        )
        builder.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        builder.configure_side_bar()
        builder.configure_selection("single")
        AgGrid(
            df,
            gridOptions=builder.build(),
            height=height,
            update_mode=GridUpdateMode.NO_UPDATE,
            allow_unsafe_jscode=True,
        )
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )
        st.caption("st-aggrid no disponible, usando tabla nativa.")
