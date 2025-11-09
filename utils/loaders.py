"""Data loading and normalization utilities for the dashboard."""

from __future__ import annotations

import io
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple, Union

import pandas as pd
import streamlit as st

from . import metrics

EXPECTED_COLUMNS = [
    "rut",
    "nombre",
    "cargo",
    "sede",
    "tipo_registro",
    "subtipo",
    "fecha_inicio",
    "fecha_termino",
    "dias",
    "horas",
    "estado",
    "observacion",
    "turno_codigo",
    "turno_inicio",
    "turno_fin",
]

REQUIRED_COLUMNS = {"rut", "nombre", "sede", "tipo_registro", "fecha_inicio", "fecha_termino"}


def _slug(text: str) -> str:
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return (
        text.replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace(".", "_")
    )


def _ensure_buffer(
    source: Union[str, Path, bytes, io.BytesIO],
) -> Tuple[Union[str, Path, io.BytesIO], Optional[str]]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        return path, path.suffix.lower()
    if isinstance(source, bytes):
        return io.BytesIO(source), None
    if isinstance(source, io.BytesIO):
        source.seek(0)
        return source, None
    if hasattr(source, "read"):
        data = source.read()
        return io.BytesIO(data), getattr(source, "name", None)
    raise ValueError("Fuente de datos no soportada")


def _read_df(handle, ext: Optional[str], **kwargs) -> pd.DataFrame:
    if isinstance(handle, (str, Path)):
        ext = Path(handle).suffix.lower()
    if ext in {".xlsx", ".xls", ".xlsm"}:
        try:
            return pd.read_excel(handle, sheet_name="BBDD", **kwargs)
        except ValueError:
            if hasattr(handle, "seek"):
                handle.seek(0)
            return pd.read_excel(handle, **kwargs)
    if ext == ".parquet":
        return pd.read_parquet(handle, **kwargs)
    if ext == ".csv":
        return pd.read_csv(handle, sep=None, engine="python", **kwargs)
    try:
        return pd.read_excel(handle, **kwargs)
    except Exception:
        handle.seek(0)
    return pd.read_csv(handle, sep=None, engine="python", **kwargs)


def peek_columns(source: Union[str, Path, bytes]) -> Iterable[str]:
    handle, ext = _ensure_buffer(source)
    df = _read_df(handle, ext, nrows=0)
    return df.columns.tolist()


def _build_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> Dict[str, str]:
    rename_map: Dict[str, str] = {}
    normalized = {_slug(col): col for col in df.columns}
    for target in EXPECTED_COLUMNS:
        configured = mapping.get(target)
        slug = _slug(configured or target)
        if configured and configured in df.columns:
            rename_map[configured] = target
        elif slug in normalized:
            rename_map[normalized[slug]] = target
        elif target in df.columns:
            rename_map[target] = target
    return rename_map


def _normalize_sede(value: str, equivalencias: Dict[str, str]) -> str:
    base = _slug(value)
    equivalencias_slug = {_slug(k): v for k, v in equivalencias.items()}
    if base in equivalencias_slug:
        return equivalencias_slug[base]
    allowed = {
        "quilpue": "Quilpué",
        "villa_alemana": "Villa Alemana",
        "vina_del_mar": "Viña del Mar",
    }
    return allowed.get(base, str(value).title())


def _title_or_none(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"sin tipo", "sin subtipo"}:
        return None
    return text.title()


def _normalize_dataframe(
    df: pd.DataFrame,
    mapping: Dict[str, str],
    equivalencias: Dict[str, str],
    reglas: Dict[str, str],
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    rename_map = _build_mapping(df, mapping)
    df = df.rename(columns=rename_map)

    for column in EXPECTED_COLUMNS:
        if column not in df.columns:
            df[column] = None

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Faltan columnas obligatorias: {', '.join(missing)}. Revisa el mapeo desde la barra lateral."
        )

    df = df[EXPECTED_COLUMNS]
    df["sede"] = df["sede"].apply(
        lambda x: _normalize_sede(x, equivalencias)
        if pd.notna(x) and str(x).strip()
        else None
    )

    for col in ["fecha_inicio", "fecha_termino", "turno_inicio", "turno_fin"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    df["dias"] = pd.to_numeric(df["dias"], errors="coerce")
    df["horas"] = pd.to_numeric(df["horas"], errors="coerce")

    def compute_row_days(row):
        if pd.notna(row["dias"]):
            return row["dias"]
        tipo = _slug(row["tipo_registro"])
        regla = reglas.get(tipo, "naturales")
        return metrics.days_between(
            row["fecha_inicio"], row["fecha_termino"], regla, row.get("horas")
        )

    df["dias"] = df.apply(compute_row_days, axis=1).fillna(0)

    for col in ["fecha_inicio", "fecha_termino"]:
        try:
            df[col] = df[col].dt.tz_localize(None)
        except (TypeError, AttributeError):
            pass

    df["estado"] = df["estado"].fillna("Pendiente").str.title()
    df["tipo_registro"] = df["tipo_registro"].apply(_title_or_none)
    df["subtipo"] = df["subtipo"].apply(_title_or_none)
    return df


@st.cache_data(show_spinner=False)
def _cached_load(
    cache_key: str,
    path_str: Optional[str],
    payload: Optional[bytes],
    mapping: Dict[str, str],
    equivalencias: Dict[str, str],
    reglas: Dict[str, str],
) -> pd.DataFrame:
    _ = cache_key
    source = io.BytesIO(payload) if payload is not None else path_str
    handle, ext = _ensure_buffer(source)
    frame = _read_df(handle, ext)
    return _normalize_dataframe(frame, mapping, equivalencias, reglas)


def load_data(
    source: Union[str, Path, bytes],
    mapping: Dict[str, str],
    equivalencias: Dict[str, str],
    reglas: Dict[str, str],
) -> pd.DataFrame:
    try:
        if isinstance(source, (str, Path)):
            path = Path(source)
            cache_key = f"path::{path.resolve()}::{path.stat().st_mtime}"
            return _cached_load(cache_key, str(path), None, mapping, equivalencias, reglas)
        data_bytes = source if isinstance(source, bytes) else source.getvalue()
        cache_key = f"upload::{hash(data_bytes)}"
        return _cached_load(cache_key, None, data_bytes, mapping, equivalencias, reglas)
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "No fue posible cargar el archivo. Revisa que el formato sea válido y que las columnas estén correctamente mapeadas."
        ) from exc


def load_catalogs(base_path: Union[str, Path]) -> Dict[str, Union[list, Dict[str, list]]]:
    base_path = Path(base_path)
    if not base_path.exists():
        return {}
    try:
        tipos_df = pd.read_excel(base_path, sheet_name="Tipos")
    except ValueError:
        return {}
    catalogos: Dict[str, Union[list, Dict[str, list]]] = {}
    catalogos["tipos"] = sorted(
        tipos_df["tipo_registro"].dropna().astype(str).str.title().unique().tolist()
    )
    catalogos["estados"] = sorted(
        tipos_df["estado"].dropna().astype(str).str.title().unique().tolist()
    )
    catalogos["sedes"] = sorted(
        tipos_df["sede"].dropna().astype(str).str.title().unique().tolist()
    )
    catalogos["cargos"] = sorted(
        tipos_df["cargo"].dropna().astype(str).str.title().unique().tolist()
    )
    subtipo_map: Dict[str, list] = {}
    for tipo, subset in tipos_df.groupby("tipo_registro"):
        if pd.isna(tipo):
            continue
        key = str(tipo).title()
        valores = sorted(
            subset["subtipo"].dropna().astype(str).str.title().unique().tolist()
        )
        if valores:
            subtipo_map[key] = valores
    catalogos["subtipos"] = subtipo_map
    return catalogos


def load_staff(base_path: Union[str, Path]) -> pd.DataFrame:
    base_path = Path(base_path)
    if not base_path.exists():
        return pd.DataFrame(columns=["rut", "nombre", "cargo", "sede"])
    try:
        staff = pd.read_excel(
            base_path,
            sheet_name="BBDD",
            usecols=["rut", "nombre", "cargo", "sede"],
        )
    except ValueError:
        return pd.DataFrame(columns=["rut", "nombre", "cargo", "sede"])
    return staff.dropna(subset=["rut", "nombre"]).drop_duplicates()


def save_dataset(df: pd.DataFrame, base_path: Union[str, Path]) -> None:
    base_path = Path(base_path)
    df_out = df.copy()
    for column in EXPECTED_COLUMNS:
        if column not in df_out.columns:
            df_out[column] = None
    df_out = df_out[EXPECTED_COLUMNS]
    writer_kwargs = {"engine": "openpyxl"}
    if base_path.exists():
        writer_kwargs.update({"mode": "a", "if_sheet_exists": "replace"})
    with pd.ExcelWriter(base_path, **writer_kwargs) as writer:
        df_out.to_excel(writer, sheet_name="BBDD", index=False)
