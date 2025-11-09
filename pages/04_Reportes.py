from __future__ import annotations

from datetime import datetime
from typing import List

import pandas as pd
import streamlit as st

from app import (
    BASE_DIR,
    apply_filters_to,
    filter_chips,
    filters_summary_text,
    get_events_df,
    use_app_shell,
)
from components import card, render_empty_state
from utils import charts, exports, metrics

TIPOS_REGISTRO = [
    "Permiso",
    "Covid",
    "Descanso compensatorio",
    "Licencia médica",
    "Vacaciones",
    "Turno",
]

DEFAULT_COLUMNS = [
    "rut",
    "nombre",
    "sede",
    "tipo_registro",
    "subtipo",
    "fecha_inicio",
    "fecha_termino",
    "dias",
    "estado",
]


def _match_tipo(valor: str, seleccion: List[str]) -> bool:
    if not seleccion:
        return True
    valor_norm = (valor or "").lower()
    return any(opc.lower() in valor_norm for opc in seleccion)


def main():
    topbar = use_app_shell("Reportes", "Reportes / Export Builder", active_page="Reportes", compact_sidebar=True)
    events = get_events_df()
    if events is None or events.empty:
        render_empty_state("Sin registros", "Selecciona una fuente de datos para habilitar las exportaciones.")
        return

    filtered, filters_state = apply_filters_to(
        events,
        state_key="reportes_filters",
        chips=["Quilpué", "Villa Alemana", "Viña del Mar"],
        prefix="reportes",
    )
    topbar(filter_chips(filters_state))
    if filtered.empty:
        render_empty_state("Sin coincidencias", "Ajusta los filtros para preparar un reporte.")
        return

    st.caption(f"{len(filtered)} registros | {filtered['rut'].nunique()} personas filtradas")

    with card("Configura el reporte"):
        col_filters = st.columns(2)
        with col_filters[0]:
            sedes = sorted(filtered["sede"].dropna().unique().tolist())
            selected_sedes = st.multiselect(
                "Sedes",
                sedes,
                default=sedes,
                placeholder="Todas las sedes",
            )
        with col_filters[1]:
            selected_tipos = st.multiselect(
                "Tipo de registro",
                TIPOS_REGISTRO,
                default=TIPOS_REGISTRO,
                placeholder="Todos los tipos",
            )

        search_cols = st.columns(2)
        with search_cols[0]:
            rut_filter = st.text_input("Buscar por RUT", placeholder="Ej: 12.345.678-9")
        with search_cols[1]:
            nombre_filter = st.text_input("Buscar por nombre", placeholder="Ej: Juan Pérez")

        min_fecha = pd.to_datetime(filtered["fecha_inicio"]).min()
        max_fecha = pd.to_datetime(filtered["fecha_inicio"]).max()
        date_range = st.date_input(
            "Rango de fechas",
            value=(min_fecha.date(), max_fecha.date()),
            format="DD/MM/YYYY",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            date_start, date_end = date_range
        else:
            date_start, date_end = min_fecha.date(), max_fecha.date()

    export_df = filtered.copy()
    if selected_sedes:
        export_df = export_df[export_df["sede"].isin(selected_sedes)]
    if selected_tipos:
        export_df = export_df[export_df["tipo_registro"].apply(lambda v: _match_tipo(v, selected_tipos))]
    if rut_filter:
        export_df = export_df[export_df["rut"].astype(str).str.contains(rut_filter, case=False, na=False)]
    if nombre_filter:
        export_df = export_df[export_df["nombre"].str.contains(nombre_filter, case=False, na=False)]
    export_df = export_df[
        (export_df["fecha_inicio"] >= pd.Timestamp(date_start))
        & (export_df["fecha_inicio"] <= pd.Timestamp(date_end))
    ]

    if export_df.empty:
        render_empty_state("Sin datos tras aplicar los filtros", "Amplía el rango o selecciona más opciones.")
        return

    available_columns = export_df.columns.tolist()
    default_columns = [col for col in DEFAULT_COLUMNS if col in available_columns]

    with card("Salida del archivo"):
        st.markdown('<div class="export-controls">', unsafe_allow_html=True)
        formato = st.radio(
            "Formato de archivo",
            ["CSV", "XLSX", "PDF"],
            index=0,
            horizontal=True,
            key="reportes-format",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        columns = st.multiselect(
            "Columnas a exportar",
            available_columns,
            default=default_columns if default_columns else available_columns,
            help="Selecciona las columnas que deseas incluir en el archivo.",
        )
        filename_base = st.text_input("Nombre base del archivo", value="reporte_rrhh")

        if st.button("Generar archivo", type="primary", use_container_width=True):
            if not columns:
                st.warning("Selecciona al menos una columna para exportar.")
                return
            subset = export_df[columns]
            stamp = datetime.now().strftime("%Y%m%d_%H%M")
            filters_text = filters_summary_text(filters_state)
            with st.spinner("Preparando archivo..."):
                if formato == "CSV":
                    data = subset.to_csv(index=False).encode("utf-8")
                    mime = "text/csv"
                    ext = "csv"
                elif formato == "XLSX":
                    buffer = exports.export_excel(
                        subset,
                        {"totales": metrics.kpi_totals(export_df), "pivote": metrics.dias_por_sede(export_df)},
                        metrics.resumen_turnos(export_df),
                    )
                    data = buffer.getvalue()
                    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ext = "xlsx"
                else:
                    kpis_payload = [
                        {
                            "label": row["tipo_registro"],
                            "value": f"{int(row['registros']):,}".replace(",", "."),
                            "note": f"{row['dias']:.1f} días",
                        }
                        for row in metrics.kpi_totals(export_df).to_dict("records")
                    ]
                    pdf_bytes = exports.export_pdf(
                        subset,
                        kpis_payload,
                        [charts.line_monthly(export_df), charts.bar_sede(export_df), charts.donut_tipo(export_df)],
                        BASE_DIR / "templates" / "reporte.html",
                        BASE_DIR / "assets" / "logo.png",
                        filtros=filters_text,
                        titulo="Reporte RR.HH.",
                    )
                    data = pdf_bytes
                    mime = "application/pdf"
                    ext = "pdf"
            st.download_button(
                "Descargar archivo",
                data=data,
                file_name=f"{filename_base}_{stamp}.{ext}",
                mime=mime,
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
