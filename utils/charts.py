"""Plotly chart helpers with the AndusChile aesthetic."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from . import metrics
from .colors import CHART_SEQUENCE, PALETTE, plotly_layout, with_alpha


def line_monthly(df: pd.DataFrame) -> go.Figure:
    trend = metrics.monthly_trend(df)
    if trend.empty:
        fig = go.Figure()
        fig.update_layout(**plotly_layout(title="Sin datos para el rango seleccionado"))
        return fig

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend["mes"],
            y=trend["registros"],
            mode="lines",
            name="Registros",
            line=dict(color=PALETTE["primary"], width=3, shape="spline"),
            fill="tozeroy",
            fillcolor=with_alpha(PALETTE["primary"], 0.18),
        )
    )
    fig.add_trace(
        go.Bar(
            x=trend["mes"],
            y=trend["dias"],
            name="Dias",
            marker_color=with_alpha(PALETTE["accent"], 0.65),
            opacity=0.45,
        )
    )
    fig.update_layout(
        **plotly_layout(
            title="Tendencia mensual",
            xaxis_title="Mes",
            yaxis_title="Cantidad",
        )
    )
    return fig


def bar_sede(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    grouped = (
        df.groupby(["sede", "tipo_registro"])
        .size()
        .reset_index(name="registros")
    )
    fig = px.bar(
        grouped,
        x="sede",
        y="registros",
        color="tipo_registro",
        barmode="stack",
        title="Distribucion por sede y tipo",
        color_discrete_sequence=CHART_SEQUENCE,
    )
    fig.update_layout(**plotly_layout())
    return fig


def donut_tipo(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure()
    grouped = (
        df.groupby("tipo_registro")
        .size()
        .reset_index(name="registros")
    )
    fig = px.pie(
        grouped,
        names="tipo_registro",
        values="registros",
        hole=0.45,
        title="Participacion por tipo de registro",
        color_discrete_sequence=CHART_SEQUENCE,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(**plotly_layout(showlegend=False))
    return fig


def bar_top_personas(df: pd.DataFrame, metric: str = "dias") -> go.Figure:
    top = metrics.top_personas(df, metric=metric)
    if top.empty:
        return go.Figure()
    fig = px.bar(
        top,
        x=metric,
        y="nombre",
        orientation="h",
        color=metric,
        title=f"Top personas por {metric}",
        color_continuous_scale=[with_alpha(PALETTE["primary"], 0.08), PALETTE["primary"]],
    )
    fig.update_layout(
        **plotly_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
        )
    )
    return fig


def heatmap_turnos(turnos: pd.DataFrame) -> go.Figure:
    if turnos.empty:
        return go.Figure()
    matrix = (
        turnos.pivot_table(
            index="nombre",
            columns=turnos["mes"].dt.strftime("%Y-%m"),
            values="tipo_registro",
            aggfunc="count",
            fill_value=0,
        )
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=list(matrix.columns),
            y=list(matrix.index),
            colorscale=[
                [0.0, with_alpha(PALETTE["primary"], 0.04)],
                [1.0, PALETTE["primary"]],
            ],
            colorbar=dict(title="Turnos"),
        )
    )
    fig.update_layout(
        **plotly_layout(
            title="Heatmap de turnos persona - mes",
            xaxis_title="Mes",
            yaxis_title="Persona",
        )
    )
    return fig
