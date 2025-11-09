"""Filter helpers, defaults and query-param sync utilities."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Dict, List, Mapping, Tuple

import pandas as pd

DEFAULT_FILTERS = {
    "sede": [],
    "personas": [],
    "tipo": [],
    "subtipo": [],
    "estado": [],
    "anios": [],
    "meses": [],
    "fecha_rango": (None, None),
}


def default_filters() -> Dict:
    return deepcopy(DEFAULT_FILTERS)


def apply_filters(df: pd.DataFrame, filtros: Dict) -> pd.DataFrame:
    filtered = df.copy()
    if filtered.empty:
        return filtered
    if filtros.get("sede"):
        filtered = filtered[filtered["sede"].isin(filtros["sede"])]
    if filtros.get("personas"):
        filtered = filtered[filtered["nombre"].isin(filtros["personas"])]
    if filtros.get("tipo"):
        filtered = filtered[filtered["tipo_registro"].isin(filtros["tipo"])]
    if filtros.get("subtipo"):
        filtered = filtered[filtered["subtipo"].isin(filtros["subtipo"])]
    if filtros.get("estado"):
        filtered = filtered[filtered["estado"].isin(filtros["estado"])]
    if filtros.get("anios"):
        filtered = filtered[
            filtered["fecha_inicio"].dt.year.isin(set(filtros["anios"]))
        ]
    if filtros.get("meses"):
        filtered = filtered[
            filtered["fecha_inicio"].dt.month.isin(set(filtros["meses"]))
        ]
    if filtros.get("fecha_rango"):
        start, end = filtros["fecha_rango"]
        if start:
            filtered = filtered[filtered["fecha_inicio"] >= pd.Timestamp(start)]
        if end:
            filtered = filtered[filtered["fecha_inicio"] <= pd.Timestamp(end)]
    return filtered


def list_options(df: pd.DataFrame) -> Dict[str, List]:
    if df.empty:
        return {key: [] for key in DEFAULT_FILTERS if key != "fecha_rango"}
    return {
        "sedes": sorted(df["sede"].dropna().unique().tolist()),
        "personas": sorted(df["nombre"].dropna().unique().tolist()),
        "tipos": sorted(df["tipo_registro"].dropna().unique().tolist()),
        "subtipos": sorted(df["subtipo"].dropna().unique().tolist()),
        "estados": sorted(df["estado"].dropna().unique().tolist()),
        "anios": sorted(df["fecha_inicio"].dt.year.dropna().unique().tolist()),
        "meses": sorted(df["fecha_inicio"].dt.month.dropna().unique().tolist()),
    }


def to_query_params(filters: Dict, prefix: str = "flt") -> Dict[str, str]:
    params: Dict[str, str] = {}
    for key, value in filters.items():
        qp_key = f"{prefix}_{key}"
        if key == "fecha_rango":
            start, end = value or (None, None)
            if start:
                params[f"{qp_key}_start"] = start.isoformat()
            if end:
                params[f"{qp_key}_end"] = end.isoformat()
        elif isinstance(value, list) and value:
            params[qp_key] = ",".join(str(v) for v in value)
    return params


def from_query_params(
    params: Mapping[str, List[str]],
    defaults: Dict,
    prefix: str = "flt",
) -> Dict:
    filters = deepcopy(defaults)
    for key in defaults.keys():
        qp_key = f"{prefix}_{key}"
        if key == "fecha_rango":
            start = params.get(f"{qp_key}_start", [None])[0]
            end = params.get(f"{qp_key}_end", [None])[0]
            filters["fecha_rango"] = (
                date.fromisoformat(start) if start else None,
                date.fromisoformat(end) if end else None,
            )
        else:
            raw = params.get(qp_key, [])
            if raw:
                tokens = [token for token in raw[0].split(",") if token]
                filters[key] = tokens
    return filters
