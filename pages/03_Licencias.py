from __future__ import annotations

import streamlit as st

from app import apply_filters_to, filter_chips, get_events_df, use_app_shell
from components import card, render_data_table, render_empty_state, render_kpi_card
from components.KpiCard import KpiModel
from utils import charts


def _licencia_kpis(df):
    criticas = df[df["dias"] > 15].shape[0]
    return [
        KpiModel("Licencias", str(len(df)), "Total en el rango"),
        KpiModel("Dias acumulados", f"{df['dias'].sum():.1f}", "Naturales"),
        KpiModel("Criticas (>15d)", str(criticas), "Requieren seguimiento"),
    ]


def main():
    topbar = use_app_shell("Licencias médicas", "Licencias / Seguimiento", active_page="Licencias", compact_sidebar=True)
    events = get_events_df()
    if events is None or events.empty:
        render_empty_state(
            "Sin licencias registradas",
            "Carga tu base para revisar el detalle de licencias médicas.",
        )
        return

    filtered_all, filters_state = apply_filters_to(
        events,
        state_key="licencias_filters",
        chips=["Quilpué", "Villa Alemana", "Viña del Mar"],
        prefix="licencias",
    )
    topbar(filter_chips(filters_state))
    licencias = filtered_all[
        filtered_all["tipo_registro"].str.contains("licencia", case=False, na=False)
    ]
    if licencias.empty:
        render_empty_state(
            "No hay licencias",
            "Usa otro rango de fechas o limpia los filtros.",
        )
        return

    cols = st.columns(len(_licencia_kpis(licencias)))
    for col, model in zip(cols, _licencia_kpis(licencias)):
        with col:
            render_kpi_card(model)

    with card("Tendencia de licencias") as container:
        with container:
            st.plotly_chart(charts.line_monthly(licencias), use_container_width=True)
    with card("Personas con más días") as container:
        with container:
            st.plotly_chart(charts.bar_top_personas(licencias, metric="dias"), use_container_width=True)

    licencias = licencias.assign(alerta=licencias["dias"] > 15)
    table_cols = [
        "rut",
        "nombre",
        "sede",
        "subtipo",
        "fecha_inicio",
        "fecha_termino",
        "dias",
        "estado",
        "alerta",
    ]
    render_data_table(
        licencias[table_cols],
        pinned_columns=["nombre", "sede"],
        key="licencias-table",
        title="Detalle de licencias médicas",
        description="Alertas se calculan automáticamente al superar 15 días",
    )


if __name__ == "__main__":
    main()
