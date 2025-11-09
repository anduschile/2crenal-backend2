"""Business metrics and KPI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

TZ = ZoneInfo("America/Santiago")


def _to_datetime(value) -> Optional[pd.Timestamp]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    ts = pd.to_datetime(value, dayfirst=True, errors="coerce", utc=True)
    if pd.isna(ts):
        return None
    return ts.tz_convert(TZ)


def days_between(
    inicio, termino, regla: str = "naturales", horas: Optional[float] = None
) -> Optional[float]:
    """Return number of days between two dates, applying domain rules."""
    start = _to_datetime(inicio)
    end = _to_datetime(termino)
    if start is None or end is None:
        if regla == "proporcionales" and horas is not None:
            return round(float(horas) / 8.0, 2)
        return None
    if end < start:
        start, end = end, start

    if regla == "habiles":
        business = pd.bdate_range(start.normalize(), end.normalize(), tz=TZ)
        return float(len(business))
    if regla == "proporcionales" and horas is not None:
        return round(float(horas) / 8.0, 2)

    delta = end - start
    # naturales incluyendo ambas fechas
    return float(delta.days + 1)


def _normalize_tipo(tipo: str) -> str:
    return (tipo or "").strip().title()


def kpi_totals(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby("tipo_registro")
        .agg(registros=("tipo_registro", "count"), dias=("dias", "sum"))
        .reset_index()
    )
    return grouped.sort_values("registros", ascending=False)


def dias_por_sede(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("sede")
        .agg(dias=("dias", "sum"), registros=("sede", "count"))
        .reset_index()
    )


def top_personas(df: pd.DataFrame, metric: str = "dias", n: int = 5) -> pd.DataFrame:
    metric = metric if metric in ("dias", "registros") else "dias"
    agg_col = "dias" if metric == "dias" else "tipo_registro"
    series = (
        df.groupby(["rut", "nombre"])
        .agg(
            dias=("dias", "sum"),
            registros=("tipo_registro", "count"),
        )
        .reset_index()
        .sort_values(metric, ascending=False)
        .head(n)
    )
    return series


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["mes", "registros", "dias"])
    tmp = df.copy()
    tmp["mes"] = pd.to_datetime(tmp["fecha_inicio"]).dt.to_period("M").dt.to_timestamp()
    grouped = (
        tmp.groupby("mes")
        .agg(registros=("tipo_registro", "count"), dias=("dias", "sum"))
        .reset_index()
        .sort_values("mes")
    )
    grouped["mes_label"] = grouped["mes"].dt.strftime("%Y-%m")
    return grouped


def ausentismo_relativo(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    personas = df["rut"].nunique()
    dias = df["dias"].sum()
    if personas == 0:
        return 0.0
    return round(float(dias) / personas, 2)


def tasa_mensual(df: pd.DataFrame, headcount: Optional[int] = None) -> pd.DataFrame:
    trend = monthly_trend(df)
    if trend.empty:
        trend["tasa"] = []
        return trend
    personas = headcount or max(df["rut"].nunique(), 1)
    trend["tasa"] = (trend["registros"] / personas) * 100
    trend["tasa"] = trend["tasa"].round(2)
    return trend


def turnos_dataset(df: pd.DataFrame) -> pd.DataFrame:
    turnos = df[df["tipo_registro"].str.lower() == "turno"].copy()
    if turnos.empty:
        return turnos
    for col in ["turno_inicio", "turno_fin"]:
        turnos[col] = pd.to_datetime(turnos[col], errors="coerce")
    turnos["duracion_horas"] = (
        (turnos["turno_fin"] - turnos["turno_inicio"]).dt.total_seconds() / 3600.0
    )
    turnos["duracion_horas"] = turnos["duracion_horas"].fillna(
        turnos["horas"]
    ).fillna(0)
    turnos["mes"] = pd.to_datetime(turnos["turno_inicio"].fillna(turnos["fecha_inicio"]))
    turnos["mes"] = turnos["mes"].dt.to_period("M").dt.to_timestamp()
    turnos["es_nocturno"] = turnos["turno_inicio"].dt.hour.isin([20, 21, 22, 23]).fillna(
        False
    )
    turnos["es_fin_semana"] = (
        turnos["turno_inicio"].dt.weekday.isin([5, 6]).fillna(False)
    )
    return turnos


def resumen_turnos(turnos: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    if turnos.empty:
        empty = pd.DataFrame(columns=["nombre", "turnos", "horas"])
        return {
            "resumen": empty,
            "tipo": empty,
            "mes": empty,
            "heatmap": empty,
            "nocturnos": empty,
        }

    resumen = (
        turnos.groupby(["rut", "nombre"])
        .agg(
            turnos=("tipo_registro", "count"),
            horas=("duracion_horas", "sum"),
            nocturnos=("es_nocturno", "sum"),
            fines_semana=("es_fin_semana", "sum"),
        )
        .reset_index()
    )

    por_tipo = (
        turnos.groupby(["sede", "turno_codigo"])
        .size()
        .reset_index(name="turnos")
        .sort_values("turnos", ascending=False)
    )

    por_mes = (
        turnos.groupby(["mes", "sede"])
        .size()
        .reset_index(name="turnos")
        .sort_values("mes")
    )

    heatmap = (
        turnos.pivot_table(
            index="nombre",
            columns=turnos["mes"].dt.strftime("%Y-%m"),
            values="tipo_registro",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )

    nocturnos = (
        turnos[turnos["es_nocturno"]]
        .groupby(["nombre"])
        .size()
        .reset_index(name="nocturnos")
        .sort_values("nocturnos", ascending=False)
    )

    return {
        "resumen": resumen,
        "tipo": por_tipo,
        "mes": por_mes,
        "heatmap": heatmap,
        "nocturnos": nocturnos,
    }
