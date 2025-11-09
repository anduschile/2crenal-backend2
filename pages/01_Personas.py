from __future__ import annotations

import streamlit as st

from app import apply_filters_to, filter_chips, get_dataset, use_app_shell
from components import card, render_data_table, render_empty_state, render_kpi_card
from components.KpiCard import KpiModel
from utils import charts


def _personas_kpis(df):
    return [
        KpiModel("Personas únicas", f"{df['rut'].nunique():,}".replace(",", "."), "En el rango seleccionado"),
        KpiModel("Sedes activas", str(df["sede"].nunique()), "Con registros recientes"),
        KpiModel("Registros", f"{len(df):,}".replace(",", "."), f"{df['dias'].sum():.1f} días"),
    ]


def main():
    topbar = use_app_shell("Personas", "Personas / Maestro", active_page="Personas", compact_sidebar=True)
    dataset = get_dataset()
    if dataset is None or dataset.empty:
        render_empty_state(
            "Sin datos",
            "Cambia la fuente en la barra lateral para comenzar a trabajar con el maestro de personas.",
        )
        return

    filtered, filters_state = apply_filters_to(
        dataset,
        state_key="personas_filters",
        chips=["Quilpué", "Villa Alemana", "Viña del Mar"],
        prefix="personas",
    )
    topbar(filter_chips(filters_state))
    if filtered.empty:
        render_empty_state(
            "No hay coincidencias",
            "Prueba con otro rango de fechas o limpia los filtros.",
        )
        return

    cols = st.columns(len(_personas_kpis(filtered)))
    for col, model in zip(cols, _personas_kpis(filtered)):
        with col:
            render_kpi_card(model)

    chart_row = st.columns(2)
    with chart_row[0]:
        with card("Distribución por sede", "Comparativo de registros") as container:
            with container:
                st.plotly_chart(charts.bar_sede(filtered), use_container_width=True)
    with chart_row[1]:
        with card("Participación por tipo") as container:
            with container:
                st.plotly_chart(charts.donut_tipo(filtered), use_container_width=True)

    table_cols = [
        "rut",
        "nombre",
        "cargo",
        "sede",
        "tipo_registro",
        "subtipo",
        "fecha_inicio",
        "fecha_termino",
        "dias",
        "estado",
    ]
    render_data_table(
        filtered[table_cols],
        pinned_columns=["nombre", "sede"],
        key="personas-table",
        title="Detalle maestro",
        description="Tabla editable desde la fuente original",
    )


if __name__ == "__main__":
    main()
