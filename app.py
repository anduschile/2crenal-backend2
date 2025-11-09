from __future__ import annotations

import copy
from datetime import date
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import yaml

from components import (
    TopbarChip,
    card,
    render_empty_state,
    render_filters_bar,
    render_kpi_card,
    render_sidebar_nav,
    render_topbar,
)
from components.KpiCard import KpiModel
from utils import charts, filters as filter_utils, loaders, metrics

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
STYLES_PATH = BASE_DIR / "assets" / "styles.css"
LOGO_PATH = BASE_DIR / "assets" / "logo.png"
BASE_DATA_FILE = BASE_DIR / "data" / "base_maestra.xlsx"
EXAMPLE_PATH = BASE_DIR / "data" / "ejemplo_base.xlsx"


def configure_page() -> None:
    st.set_page_config(
        page_title="Centro Renal SPA – Dashboard RR.HH.",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def _load_yaml(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_styles(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@st.cache_resource(show_spinner=False)
def load_config() -> Dict:
    return _load_yaml(CONFIG_PATH)


@st.cache_resource(show_spinner=False)
def load_styles() -> str:
    return _load_styles(STYLES_PATH)


def inject_styles() -> None:
    st.markdown(f"<style>{load_styles()}</style>", unsafe_allow_html=True)


def init_app_state() -> None:
    config = load_config()
    st.session_state.setdefault("config", config)
    st.session_state.setdefault("column_mapping", copy.deepcopy(config.get("column_mapping", {})))
    default_source = "Base maestra" if BASE_DATA_FILE.exists() else "Archivo de ejemplo"
    st.session_state.setdefault("data_source", default_source)
    st.session_state.setdefault("uploaded_payload", None)
    st.session_state.setdefault("dataset", None)
    st.session_state.setdefault("events_df", None)
    st.session_state.setdefault("filter_options", {})
    st.session_state.setdefault("dataset_signature", None)


def _dataset_signature(option: str) -> str:
    if option == "Base maestra":
        return f"base::{BASE_DATA_FILE.stat().st_mtime if BASE_DATA_FILE.exists() else 'missing'}"
    if option == "Archivo de ejemplo":
        return f"example::{EXAMPLE_PATH.stat().st_mtime}"
    payload = st.session_state.get("uploaded_payload")
    return f"upload::{hash(payload) if payload else 'empty'}"


def _load_dataset(option: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, List[str]]]:
    mapping = st.session_state["column_mapping"]
    cfg = st.session_state["config"]
    equivalencias = cfg.get("sede_equivalencias", {})
    reglas = cfg.get("reglas_dias", {})
    if option == "Base maestra":
        if not BASE_DATA_FILE.exists():
            raise ValueError("No se encontró data/base_maestra.xlsx. Usa la opción de carga manual.")
        df = loaders.load_data(BASE_DATA_FILE, mapping, equivalencias, reglas)
    elif option == "Archivo de ejemplo":
        df = loaders.load_data(EXAMPLE_PATH, mapping, equivalencias, reglas)
    else:
        payload = st.session_state.get("uploaded_payload")
        if not payload:
            raise ValueError("Sube un archivo para continuar.")
        df = loaders.load_data(payload, mapping, equivalencias, reglas)
    eventos = df[df["tipo_registro"].notna()].copy()
    opciones = filter_utils.list_options(eventos if not eventos.empty else df)
    return df, eventos, opciones


def render_sidebar(active_page: str, compact: bool = False) -> None:
    with st.sidebar:
        render_sidebar_nav(active_page)
        selector = st.container()
        selector.markdown('<div class="sidebar-shell">', unsafe_allow_html=True)
        selector.markdown("<p class='eyebrow'>Datos</p><h4>Fuente activa</h4>", unsafe_allow_html=True)
        source_options = ["Base maestra", "Archivo de ejemplo", "Subir archivo"]
        data_option = selector.radio(
            "Fuente de datos",
            source_options,
            index=source_options.index(st.session_state.get("data_source", source_options[0])),
            key="data_source",
            label_visibility="collapsed" if compact else "visible",
        )
        if data_option == "Subir archivo":
            uploaded = selector.file_uploader(
                "Carga Excel/CSV/Parquet",
                type=["xlsx", "xls", "csv", "parquet"],
                accept_multiple_files=False,
                key="data_upload",
            )
            if uploaded is not None:
                st.session_state["uploaded_payload"] = uploaded.getvalue()
        selector.caption("Configura el mapeo desde la página Configuración.")
        selector.markdown("</div>", unsafe_allow_html=True)
        if st.button("Exportar CSV", key="sidebar-export"):
            st.toast("Abre la página Reportes para descargar CSV personalizados.", icon="✅")

    signature = _dataset_signature(data_option)
    if signature != st.session_state.get("dataset_signature"):
        try:
            df, eventos, opciones = _load_dataset(data_option)
        except ValueError as exc:
            st.sidebar.warning(str(exc))
            return
        except RuntimeError as exc:
            st.sidebar.error(str(exc))
            return
        st.session_state["dataset_signature"] = signature
        st.session_state["dataset"] = df
        st.session_state["events_df"] = eventos
        st.session_state["filter_options"] = opciones

    dataset = st.session_state.get("dataset")
    if dataset is not None and not dataset.empty:
        with st.sidebar:
            stats = st.container()
            stats.markdown('<div class="sidebar-shell">', unsafe_allow_html=True)
            stats.metric("Registros", len(dataset))
            stats.metric("Personas", dataset["rut"].nunique())
            stats.markdown("</div>", unsafe_allow_html=True)


def use_app_shell(
    page_title: str,
    breadcrumb: str,
    *,
    active_page: str = "app",
    compact_sidebar: bool = False,
) -> Callable[[Optional[List[TopbarChip]], Optional[Callable[[], None]]], None]:
    configure_page()
    init_app_state()
    inject_styles()
    render_sidebar(active_page, compact_sidebar)
    topbar_placeholder = st.empty()

    def _render_topbar(
        chips_override: Optional[List[TopbarChip]] = None,
        actions_override: Optional[Callable[[], None]] = None,
    ) -> None:
        with topbar_placeholder.container():
            render_topbar(
                page_title,
                breadcrumb,
                chips=chips_override,
                actions=actions_override,
            )

    _render_topbar()
    return _render_topbar


def get_dataset() -> Optional[pd.DataFrame]:
    return st.session_state.get("dataset")


def get_events_df() -> Optional[pd.DataFrame]:
    return st.session_state.get("events_df")


def get_filter_options() -> Dict[str, List[str]]:
    return st.session_state.get("filter_options", {})


def apply_filters_to(
    dataset: Optional[pd.DataFrame],
    *,
    state_key: str,
    chips: Optional[List[str]] = None,
    prefix: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict]:
    options = (
        filter_utils.list_options(dataset) if dataset is not None and not dataset.empty else filter_utils.default_filters()
    )
    filters_state = render_filters_bar(
        options if isinstance(options, dict) else {},
        state_key=state_key,
        prefix=prefix or state_key,
        chips=chips,
    )
    filtered = (
        filter_utils.apply_filters(dataset, filters_state)
        if dataset is not None and not dataset.empty
        else pd.DataFrame(columns=dataset.columns if dataset is not None else [])
    )
    return filtered, filters_state


def filters_summary_text(filters_state: Dict) -> str:
    parts = []
    if filters_state.get("sede"):
        parts.append(f"Sedes: {', '.join(filters_state['sede'])}")
    if filters_state.get("personas"):
        parts.append(f"Personas: {len(filters_state['personas'])}")
    if filters_state.get("tipo"):
        parts.append(f"Tipos: {', '.join(filters_state['tipo'])}")
    if filters_state.get("fecha_rango"):
        start, end = filters_state["fecha_rango"]
        if start or end:
            fmt = lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else d or "---"
            parts.append(f"Fechas: {fmt(start)} a {fmt(end)}")
    return " | ".join(parts) or "Sin filtros"


def filter_chips(filters_state: Dict) -> List[TopbarChip]:
    chips: List[TopbarChip] = []
    if filters_state.get("sede"):
        chips.append(TopbarChip(f"Sedes: {len(filters_state['sede'])}"))
    if filters_state.get("tipo"):
        chips.append(TopbarChip(f"Tipos: {len(filters_state['tipo'])}", variant="soft"))
    if filters_state.get("fecha_rango"):
        start, end = filters_state["fecha_rango"]
        if start or end:
            fmt = lambda d: d.strftime("%d/%m") if hasattr(d, "strftime") else d or "---"
            chips.append(TopbarChip(f"{fmt(start)} - {fmt(end)}", variant="soft"))
    if not chips:
        chips.append(TopbarChip("Sin filtros", variant="soft"))
    return chips


def _render_home_content(
    topbar_callback: Optional[Callable[[Optional[List[TopbarChip]], Optional[Callable[[], None]]], None]] = None,
) -> None:
    dataset = get_dataset()
    events = get_events_df()
    if dataset is None or events is None:
        render_empty_state(
            "Sin datos",
            "Selecciona una fuente desde la barra lateral para comenzar.",
        )
        return
    filtered, filters_state = apply_filters_to(
        events,
        state_key="home_filters",
        chips=["Quilpué", "Villa Alemana", "Viña del Mar"],
        prefix="home",
    )
    if topbar_callback:
        def _actions():
            st.page_link("pages/04_Reportes.py", label="Exportar CSV", icon="📁")
            st.page_link("pages/06_Registro.py", label="Nuevo registro", icon="➕")

        topbar_callback(filter_chips(filters_state), _actions)
    st.markdown(
        """
        <div class="cta-card">
            <div>
                <h3>Registrar nuevo movimiento</h3>
                <p>Ingresa permisos, licencias o vacaciones directamente desde el dashboard.</p>
            </div>
            <a class="cta-button" href="/Registro" target="_self">➕ Nuevo registro</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if filtered.empty:
        render_empty_state(
            "No hay registros",
            "Ajusta los filtros para visualizar indicadores.",
        )
        return

    trend = metrics.monthly_trend(filtered)

    def _delta_for(column: str) -> tuple[Optional[str], str]:
        if trend.empty or column not in trend or len(trend[column]) < 2:
            return None, "neutral"
        current = trend[column].iloc[-1]
        previous = trend[column].iloc[-2]
        if previous == 0:
            return None, "neutral"
        change = ((current - previous) / previous) * 100
        tone = "success" if change >= 0 else "danger"
        return f"{change:+.1f}% vs mes anterior", tone

    registros_delta, registros_tone = _delta_for("registros")
    dias_delta, dias_tone = _delta_for("dias")

    kpis = [
        KpiModel(
            "Registros",
            f"{len(filtered):,}".replace(",", "."),
            f"{filtered['dias'].sum():.1f} días otorgados",
            delta=registros_delta,
            delta_tone=registros_tone,
        ),
        KpiModel(
            "Personas",
            f"{filtered['rut'].nunique():,}".replace(",", "."),
            "Únicas en el rango",
            delta=f"{filtered['sede'].nunique()} sedes activas",
            delta_tone="neutral",
        ),
        KpiModel(
            "Días promedio",
            f"{filtered['dias'].mean():.1f}",
            "Por evento aprobado",
            delta=dias_delta,
            delta_tone=dias_tone,
        ),
    ]
    cols = st.columns(len(kpis))
    for col, model in zip(cols, kpis):
        with col:
            render_kpi_card(model)

    with card("Tendencia de KPIs", "Últimos 12 meses") as container:
        with container:
            st.plotly_chart(charts.line_monthly(filtered), use_container_width=True)

    charts_row = st.columns(2)
    with charts_row[0]:
        with card("Distribución por sede", "Stack por tipo de registro") as container:
            with container:
                st.plotly_chart(charts.bar_sede(filtered), use_container_width=True)
    with charts_row[1]:
        with card("Participación por tipo") as container:
            with container:
                st.plotly_chart(charts.donut_tipo(filtered), use_container_width=True)

    def _list_section(df: pd.DataFrame, title: str, empty_text: str, *, date_col: str | None = None):
        with card(title, classes="list-card") as container:
            with container:
                if df.empty:
                    st.caption(empty_text)
                    return
                for _, row in df.iterrows():
                    badge = row.get("estado", "Pendiente")
                    sede = row.get("sede", "Sin sede")
                    persona = row.get("nombre", "Sin nombre")
                    note = row.get("subtipo") or row.get("tipo_registro") or ""
                    if date_col and date_col in row and pd.notna(row[date_col]):
                        when = pd.to_datetime(row[date_col], errors="coerce")
                        fecha = when.strftime("%d %b") if when is not None else ""
                    else:
                        fecha = f"{row.get('dias', 0):.1f} días"
                    st.markdown(
                        f"""
                        <div class="list-item">
                            <div>
                                <strong>{persona}</strong>
                                <p>{note} · {sede}</p>
                            </div>
                            <div>
                                <span class="badge badge-info">{badge}</span>
                                <span class="chip" data-variant="soft">{fecha}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    today = pd.Timestamp.today().normalize()
    eventos = filtered.copy()
    eventos["fecha_inicio"] = pd.to_datetime(eventos.get("fecha_inicio"), errors="coerce")
    eventos["fecha_termino"] = pd.to_datetime(eventos.get("fecha_termino"), errors="coerce")

    permisos_proximos = eventos[
        eventos["tipo_registro"].str.contains("permiso", case=False, na=False)
        & (eventos["fecha_inicio"] >= today)
        & (eventos["fecha_inicio"] <= today + pd.Timedelta(days=21))
    ].sort_values("fecha_inicio").head(5)

    licencias_largas = eventos[
        eventos["tipo_registro"].str.contains("licencia", case=False, na=False)
        & (eventos["dias"] >= 15)
    ].sort_values("dias", ascending=False).head(5)

    turnos = eventos[eventos["tipo_registro"].str.contains("turno", case=False, na=False)]
    estado_mask = (
        turnos["estado"].str.contains("pendiente|crítico|critico", case=False, na=False)
        if "estado" in turnos.columns
        else pd.Series([True] * len(turnos), index=turnos.index)
    )
    turnos_criticos = turnos[estado_mask].sort_values("fecha_inicio").head(5)

    lists_row = st.columns(3)
    with lists_row[0]:
        _list_section(permisos_proximos, "Permisos próximos", "Sin permisos en las próximas 3 semanas.", date_col="fecha_inicio")
    with lists_row[1]:
        _list_section(licencias_largas, "Licencias >15 días", "Sin licencias extensas en el rango.")
    with lists_row[2]:
        _list_section(turnos_criticos, "Turnos críticos", "Todo al día.", date_col="fecha_inicio")


def run_home() -> None:
    topbar = use_app_shell("Inicio", "Dashboard / Inicio", active_page="app", compact_sidebar=True)
    _render_home_content(topbar)


if __name__ == "__main__":
    run_home()
