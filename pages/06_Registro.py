from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from app import BASE_DATA_FILE, get_dataset, use_app_shell
from components import card, render_empty_state
from utils import loaders

TIPO_EVENTO = [
    "Permiso",
    "Licencia médica",
    "Vacaciones",
    "Descanso compensatorio",
    "Turno",
    "Covid",
    "Otro",
]

ESTADOS = ["Pendiente", "Aprobado", "Rechazado"]
BUSINESS_TYPES = {"permiso", "vacaciones", "descanso compensatorio", "descanso"}


def _person_lookup(dataset: pd.DataFrame) -> Tuple[List[str], Dict[str, Dict]]:
    fields = [col for col in ["rut", "nombre", "sede", "cargo", "area"] if col in dataset.columns]
    if not fields:
        return [], {}
    base = (
        dataset[fields]
        .dropna(subset=["rut", "nombre"])
        .drop_duplicates(subset=["rut"])
        .sort_values("nombre")
    )
    options = []
    mapping: Dict[str, Dict] = {}
    for _, row in base.iterrows():
        label = f"{row['nombre']} · {row['rut']}"
        mapping[label] = row.to_dict()
        options.append(label)
    return options, mapping


def _build_row(template_cols: List[str], base: Dict, form_data: Dict) -> Dict:
    row = {col: None for col in template_cols}
    for key, value in base.items():
        if key in row:
            row[key] = value
    for key, value in form_data.items():
        if key in row:
            row[key] = value
    return row


def _date_span(start: date, end: date) -> float:
    return float((pd.Timestamp(end) - pd.Timestamp(start)).days + 1)


def _is_business_type(tipo: str) -> bool:
    return (tipo or "").strip().lower() in BUSINESS_TYPES


def _to_date(value) -> date:
    if isinstance(value, (list, tuple, np.ndarray)):
        value = value[0]
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return pd.to_datetime(value).date()


def _business_days(start: date, end: date) -> float:
    start = _to_date(start)
    end = _to_date(end)
    start_np = np.datetime64(start)
    end_np = np.datetime64(end)
    if end_np < start_np:
        start_np, end_np = end_np, start_np
    count = np.busday_count(start_np, end_np)
    if np.is_busday(end_np):
        count += 1
    return float(max(count, 1))


def _end_from_days(start: date, days: float, tipo: str) -> date:
    start = _to_date(start)
    full_days = max(int(round(days)), 1)
    if not _is_business_type(tipo):
        return start + timedelta(days=full_days - 1)
    remaining = full_days - 1
    current = start
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _days_from_range(start: date, end: date, tipo: str) -> float:
    start = _to_date(start)
    end = _to_date(end)
    if _is_business_type(tipo):
        return _business_days(start, end)
    return _date_span(start, end)


def _refresh_events():
    dataset = st.session_state.get("dataset")
    if dataset is not None:
        st.session_state["events_df"] = dataset[dataset["tipo_registro"].notna()].copy()


def main():
    use_app_shell("Registrar evento", "Registro manual / Funcionarios", active_page="Registro", compact_sidebar=True)
    dataset = get_dataset()
    if dataset is None or dataset.empty:
        render_empty_state(
            "Sin datos de funcionarios",
            "Carga una base para poder registrar permisos o licencias.",
        )
        return

    base_dataset = dataset
    sedes_disponibles = sorted(dataset["sede"].dropna().unique().tolist()) if "sede" in dataset.columns else []
    sede_filter = None
    filtered_dataset = dataset
    if sedes_disponibles:
        sede_filter = st.selectbox("Filtrar por sede", ["Todas"] + sedes_disponibles)
        if sede_filter != "Todas":
            filtered_dataset = dataset[dataset["sede"] == sede_filter]
    personas, lookup = _person_lookup(filtered_dataset)
    if not personas:
        render_empty_state(
            "Faltan columnas básicas",
            "Necesitas al menos rut y nombre para poder cargar el formulario.",
        )
        return

    st.session_state.setdefault("registro_persona", personas[0])
    default_index = 0
    try:
        default_index = personas.index(st.session_state["registro_persona"])
    except ValueError:
        st.session_state["registro_persona"] = personas[0]
        default_index = 0
    st.session_state["registro_persona"] = st.selectbox(
        "Funcionario",
        personas,
        index=default_index,
        key="registro-funcionario",
    )
    persona_info = lookup[st.session_state["registro_persona"]]

    info_cols = st.columns(len(persona_info))
    for col, (label, value) in zip(info_cols, persona_info.items()):
        with col:
            st.markdown(f"**{label.capitalize()}**")
            st.caption(str(value))

    st.session_state.setdefault("registro-start", date.today())
    st.session_state.setdefault("registro-end", date.today())
    st.session_state.setdefault("registro-days", 1.0)
    st.session_state.setdefault("registro-tipo", TIPO_EVENTO[2])

    def _sync_end_from_days():
        start_value = st.session_state.get("registro-start", date.today())
        days_value = max(float(st.session_state.get("registro-days", 1.0)), 0.5)
        current_tipo = st.session_state.get("registro-tipo", TIPO_EVENTO[0])
        st.session_state["registro-end"] = _end_from_days(start_value, days_value, current_tipo)

    def _sync_days_from_end():
        start_value = st.session_state.get("registro-start", date.today())
        end_value = st.session_state.get("registro-end", start_value)
        current_tipo = st.session_state.get("registro-tipo", TIPO_EVENTO[0])
        st.session_state["registro-days"] = max(_days_from_range(start_value, end_value, current_tipo), 0.5)

    def _range_changed():
        selected_range = st.session_state.get("registro-range")
        if isinstance(selected_range, (tuple, list, np.ndarray)) and len(selected_range) == 2:
            st.session_state["registro-start"] = _to_date(selected_range[0])
            st.session_state["registro-end"] = _to_date(selected_range[1])
        else:
            st.session_state["registro-start"] = _to_date(selected_range)
            st.session_state["registro-end"] = _to_date(selected_range)
        _sync_days_from_end()

    def _tipo_changed():
        current_tipo = st.session_state.get("registro-tipo", TIPO_EVENTO[0])
        _sync_end_from_days()
        _sync_days_from_end()

    with card("Registro de permisos/licencias"):
        st.selectbox(
            "Tipo de registro",
            TIPO_EVENTO,
            index=TIPO_EVENTO.index(st.session_state.get("registro-tipo", TIPO_EVENTO[0])),
            key="registro-tipo",
            on_change=_tipo_changed,
        )

        st.date_input(
            "Rango de fechas",
            value=(st.session_state["registro-start"], st.session_state["registro-end"]),
            key="registro-range",
            format="DD/MM/YYYY",
            on_change=_range_changed,
        )

        st.number_input(
            "Cantidad de días",
            min_value=0.5,
            value=st.session_state["registro-days"],
            step=0.5,
            key="registro-days",
            on_change=_sync_end_from_days,
        )

        with st.form("registro-form"):
            tipo = st.session_state.get("registro-tipo", TIPO_EVENTO[0])
            subtipo = st.text_input("Subtipo o motivo", placeholder="Ej: Permiso administrativo", key="registro-subtipo")
            estado = st.selectbox("Estado", ESTADOS, index=0, key="registro-estado")
            observacion = st.text_area("Observaciones", placeholder="Notas internas o número de folio", key="registro-observaciones")

            submitted = st.form_submit_button("Guardar registro", use_container_width=True)

        if submitted:
            start_date = st.session_state["registro-start"]
            end_date = st.session_state["registro-end"]
            dias = st.session_state["registro-days"]
            current_tipo = st.session_state.get("registro-tipo", TIPO_EVENTO[0])
            dias = _days_from_range(start_date, end_date, current_tipo)
            form_payload = {
                "tipo_registro": tipo,
                "subtipo": subtipo,
                "estado": estado,
                "fecha_inicio": pd.Timestamp(start_date),
                "fecha_termino": pd.Timestamp(end_date),
                "dias": float(dias),
                "observacion": observacion,
            }
            template_cols = dataset.columns.tolist()
            new_row = _build_row(template_cols, persona_info, form_payload)
            st.session_state["dataset"] = pd.concat(
                [dataset, pd.DataFrame([new_row])],
                ignore_index=True,
            )
            _refresh_events()
            if st.session_state.get("data_source") == "Base maestra" and BASE_DATA_FILE.exists():
                loaders.save_dataset(st.session_state["dataset"], BASE_DATA_FILE)
            st.success("Registro ingresado correctamente.")

    recent = st.session_state.get("dataset", pd.DataFrame()).sort_values("fecha_inicio", ascending=False).head(5)
    if not recent.empty:
        with card("Últimos movimientos capturados", description="Sólo se muestran los cinco más recientes."):
            st.dataframe(
                recent[
                    [
                        col
                        for col in ["fecha_inicio", "nombre", "tipo_registro", "subtipo", "dias", "estado"]
                        if col in recent.columns
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

    editable = base_dataset[base_dataset["tipo_registro"].notna()].copy()
    if not editable.empty:
        editable = editable.sort_values("fecha_inicio", ascending=False).head(100)
        choices = []
        mapping: Dict[str, int] = {}
        for idx, row in editable.iterrows():
            label = f"{idx} · {row.get('nombre', 'Sin nombre')} · {row.get('tipo_registro', 'Tipo')} · {row.get('fecha_inicio', ''):%d/%m/%Y}"
            choices.append(label)
            mapping[label] = idx

        with card("Editar / eliminar registro"):
            selected_label = st.selectbox("Selecciona un registro", choices, key="registro-edit-select")
            selected_idx = mapping[selected_label]
            record = dataset.loc[selected_idx]
            start_edit = pd.to_datetime(record.get("fecha_inicio")).date() if pd.notna(record.get("fecha_inicio")) else date.today()
            end_edit = pd.to_datetime(record.get("fecha_termino")).date() if pd.notna(record.get("fecha_termino")) else start_edit
            dias_edit = float(record.get("dias") or _date_span(start_edit, end_edit))
            with st.form("edit-form"):
                tipo_edit = st.selectbox("Tipo de registro", TIPO_EVENTO, index=TIPO_EVENTO.index(record.get("tipo_registro")) if record.get("tipo_registro") in TIPO_EVENTO else 0, key="edit-tipo")
                subtipo_edit = st.text_input("Subtipo o motivo", value=record.get("subtipo") or "", key="edit-subtipo")
                estado_edit = st.selectbox("Estado", ESTADOS, index=ESTADOS.index(record.get("estado")) if record.get("estado") in ESTADOS else 0, key="edit-estado")
                rango_edit = st.date_input("Rango de fechas", value=(start_edit, end_edit), format="DD/MM/YYYY", key="edit-rango")
                if isinstance(rango_edit, tuple):
                    start_edit, end_edit = rango_edit
                dias_edit = st.number_input("Cantidad de días", min_value=0.5, value=dias_edit, step=0.5, key="edit-dias")
                observacion_edit = st.text_area("Observaciones", value=record.get("observacion") or "", key="edit-observaciones")
                update = st.form_submit_button("Guardar cambios", use_container_width=True)
                delete = st.form_submit_button("Eliminar registro", use_container_width=True)

            if update:
                dataset.loc[selected_idx, "tipo_registro"] = tipo_edit
                dataset.loc[selected_idx, "subtipo"] = subtipo_edit
                dataset.loc[selected_idx, "estado"] = estado_edit
                dataset.loc[selected_idx, "fecha_inicio"] = pd.Timestamp(start_edit)
                dataset.loc[selected_idx, "fecha_termino"] = pd.Timestamp(end_edit)
                dataset.loc[selected_idx, "dias"] = float(_days_from_range(start_edit, end_edit, tipo_edit))
                dataset.loc[selected_idx, "observacion"] = observacion_edit
                st.session_state["dataset"] = dataset
                _refresh_events()
                if st.session_state.get("data_source") == "Base maestra" and BASE_DATA_FILE.exists():
                    loaders.save_dataset(dataset, BASE_DATA_FILE)
                st.success("Registro actualizado.")
            if delete:
                dataset = dataset.drop(index=selected_idx).reset_index(drop=True)
                st.session_state["dataset"] = dataset
                _refresh_events()
                if st.session_state.get("data_source") == "Base maestra" and BASE_DATA_FILE.exists():
                    loaders.save_dataset(dataset, BASE_DATA_FILE)
                st.success("Registro eliminado.")


if __name__ == "__main__":
    main()
