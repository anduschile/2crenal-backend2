from __future__ import annotations

import streamlit as st

from app import apply_filters_to, filter_chips, get_events_df, use_app_shell
from components import card, render_data_table, render_empty_state, render_kpi_card
from components.KpiCard import KpiModel
from utils import charts


def _permiso_kpis(df):
    horas = df["horas"].fillna(0).sum()
    pendiente = df[df["estado"].str.lower() == "pendiente"].shape[0]
    return [
        KpiModel("Permisos", str(len(df)), "Registros filtrados"),
        KpiModel("Horas", f"{horas:.1f}", "Totales acumuladas"),
        KpiModel("Pendientes", str(pendiente), "A la espera de aprobacion"),
    ]


def main():
    topbar = use_app_shell("Permisos", "Permisos / Bandeja", active_page="Permisos", compact_sidebar=True)
    events = get_events_df()
    if events is None or events.empty:
        render_empty_state(
            "Sin permisos registrados",
            "Importa tu base desde la pantalla principal para habilitar esta vista.",
        )
        return

    filtered_all, filters_state = apply_filters_to(
        events,
        state_key="permisos_filters",
        chips=["Quilpué", "Villa Alemana", "Viña del Mar"],
        prefix="permisos",
    )
    topbar(filter_chips(filters_state))
    permisos = filtered_all[filtered_all["tipo_registro"].str.lower() == "permiso"]
    if permisos.empty:
        render_empty_state(
            "No hay permisos",
            "Ajusta los filtros para visualizar registros.",
        )
        return

    cols = st.columns(len(_permiso_kpis(permisos)))
    for col, model in zip(cols, _permiso_kpis(permisos)):
        with col:
            render_kpi_card(model)

    with card("Tendencia de permisos") as container:
        with container:
            st.plotly_chart(charts.line_monthly(permisos), use_container_width=True)
    with card("Top personas por días") as container:
        with container:
            st.plotly_chart(charts.bar_top_personas(permisos, metric="dias"), use_container_width=True)

    table_cols = [
        "rut",
        "nombre",
        "sede",
        "subtipo",
        "fecha_inicio",
        "fecha_termino",
        "horas",
        "estado",
        "observacion",
    ]
    render_data_table(
        permisos[table_cols],
        pinned_columns=["nombre", "sede"],
        key="permisos-table",
        title="Detalle de permisos",
        description="Estatus y observaciones alineadas al registro original",
    )


if __name__ == "__main__":
    main()
