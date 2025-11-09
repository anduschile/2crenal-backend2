from __future__ import annotations

from datetime import date, datetime, timedelta
import calendar
from typing import Dict, List, Tuple, Union

import streamlit as st

from utils import filters as filter_utils


def _default_dates() -> Tuple[date, date]:
    today = date.today()
    return date(today.year, 1, 1), today


def _coerce_date(value: Union[date, datetime, str, None]) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _token(label: str) -> str:
    return f'<span class="token-pill">{label}</span>'


def _last_day(year: int, month: int) -> date:
    day = calendar.monthrange(year, month)[1]
    return date(year, month, day)


def _quick_ranges(today: date) -> Dict[str, Tuple[date, date]]:
    first_day = today.replace(day=1)
    last_day_month = _last_day(today.year, today.month)
    prev_end = first_day - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    return {
        "Mes actual": (first_day, _last_day(today.year, today.month)),
        "Mes anterior": (prev_start, _last_day(prev_start.year, prev_start.month)),
        "Últimos 30 días": (today - timedelta(days=29), today),
        "Año en curso": (date(today.year, 1, 1), date(today.year, 12, 31)),
    }


def render_filters_bar(
    options: Dict[str, List[str]],
    state_key: str = "global_filters",
    prefix: str = "flt",
    chips: List[str] | None = None,
) -> Dict:
    defaults = filter_utils.default_filters()
    filters_state = st.session_state.setdefault(state_key, defaults.copy())

    if not st.session_state.get(f"{state_key}_synced"):
        raw_qp = {}
        for key, value in st.query_params.items():
            if isinstance(value, list):
                raw_qp[key] = value
            else:
                raw_qp[key] = [value]
        filters_state = filter_utils.from_query_params(raw_qp, defaults, prefix=prefix)
        st.session_state[state_key] = filters_state
        st.session_state[f"{state_key}_synced"] = True

    chips = chips or options.get("sedes", [])
    st.markdown('<div class="filter-bar">', unsafe_allow_html=True)

    summary_tokens: List[str] = []
    if filters_state.get("sede"):
        summary_tokens.append(_token(f"Sedes · {len(filters_state['sede'])}"))
    if filters_state.get("tipo"):
        summary_tokens.append(_token(f"Tipos · {len(filters_state['tipo'])}"))
    if isinstance(filters_state.get("fecha_rango"), tuple):
        start, end = (filters_state["fecha_rango"] + (None, None))[:2]
        if start or end:
            fmt = lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else d or "---"
            summary_tokens.append(_token(f"{fmt(start)} → {fmt(end)}"))
    if summary_tokens:
        st.markdown(
            '<div class="filter-summary">' + "".join(summary_tokens) + "</div>",
            unsafe_allow_html=True,
        )

    grid = st.columns(2)
    with grid[0]:
        sede_opts = chips
        current_sedes = [s for s in filters_state.get("sede", []) if s in sede_opts]
        filters_state["sede"] = st.multiselect(
            "Sedes",
            sede_opts,
            default=current_sedes,
            placeholder="Todas las sedes",
            key=f"{state_key}-sedes",
        )
    with grid[1]:
        tipo_opts = options.get("tipos", [])
        current_tipos = [t for t in filters_state.get("tipo", []) if t in tipo_opts]
        filters_state["tipo"] = st.multiselect(
            "Tipos de registro",
            tipo_opts,
            default=current_tipos,
            placeholder="Todos los tipos",
            key=f"{state_key}-tipos",
        )

    stored_range = filters_state.get("fecha_rango")
    if (
        not stored_range
        or not isinstance(stored_range, tuple)
        or len(stored_range) != 2
    ):
        stored_range = _default_dates()
    fallback_start, fallback_end = _default_dates()
    start_val = stored_range[0] if len(stored_range) > 0 else None
    end_val = stored_range[1] if len(stored_range) > 1 else None
    start_default = _coerce_date(start_val) or fallback_start
    end_default = _coerce_date(end_val) or fallback_end

    date_key = f"{state_key}-dates"
    if date_key not in st.session_state:
        st.session_state[date_key] = (start_default, end_default)

    def _apply_range(new_range: Tuple[date, date]):
        filters_state["fecha_rango"] = new_range
        st.session_state[state_key] = filters_state
        params = filter_utils.to_query_params(filters_state, prefix=prefix)
        st.query_params = params

    quick_ranges = _quick_ranges(date.today())
    quick_cols = st.columns(len(quick_ranges) + 1)
    for idx, (label, (start_q, end_q)) in enumerate(quick_ranges.items()):
        if quick_cols[idx].button(label, key=f"{state_key}-quick-{label}"):
            st.session_state[date_key] = (start_q, end_q)
            _apply_range((start_q, end_q))
            st.rerun()
    if quick_cols[-1].button("Reiniciar fechas", key=f"{state_key}-quick-reset"):
        new_range = _default_dates()
        st.session_state[date_key] = new_range
        _apply_range(new_range)
        st.rerun()

    layout_bottom = st.columns((3, 1))
    with layout_bottom[0]:
        st.date_input(
            "Rango de fechas",
            value=st.session_state[date_key],
            format="DD/MM/YYYY",
            key=date_key,
        )
        selected_value = st.session_state[date_key]
        if isinstance(selected_value, tuple):
            start_date = _coerce_date(selected_value[0]) or st.session_state[date_key][0]
            end_date = _coerce_date(selected_value[1]) or st.session_state[date_key][1]
        else:
            start_date = end_date = _coerce_date(selected_value) or st.session_state[date_key][0]
        _apply_range((start_date, end_date))
    with layout_bottom[1]:
        st.markdown("<div class='filter-actions'>", unsafe_allow_html=True)
        if st.button("Borrar filtros", key=f"{state_key}-clear", use_container_width=True):
            filters_state = filter_utils.default_filters()
            st.session_state[state_key] = filters_state
            params = filter_utils.to_query_params(filters_state, prefix=prefix)
            st.query_params = params
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            return filters_state
        st.markdown("</div>", unsafe_allow_html=True)

    st.session_state[state_key] = filters_state
    params = filter_utils.to_query_params(filters_state, prefix=prefix)
    st.query_params = params
    st.markdown("</div>", unsafe_allow_html=True)
    return filters_state
