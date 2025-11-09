"""Helpers to export filtered data to Excel and PDF."""

from __future__ import annotations

import base64
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

EXPORT_FMT = "%Y%m%d_%H%M"


def _fig_to_uri(fig) -> Optional[str]:
    if fig is None:
        return None
    try:
        png = fig.to_image(format="png", scale=2)
    except Exception:
        return None
    b64 = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"


def export_excel(
    df: pd.DataFrame,
    resumen: Dict[str, pd.DataFrame],
    turnos: Dict[str, pd.DataFrame],
) -> io.BytesIO:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Detalle", index=False)

        resumen_sheet = resumen.get("totales")
        if resumen_sheet is not None:
            resumen_sheet.to_excel(writer, sheet_name="Resumen", index=False)

        turnos_sheet = turnos.get("resumen")
        if turnos_sheet is not None:
            turnos_sheet.to_excel(writer, sheet_name="Turnos", index=False)

        pivote = resumen.get("pivote")
        if pivote is not None:
            pivote.to_excel(writer, sheet_name="Pivotes", index=False)

        workbook = writer.book
        fmt_header = workbook.add_format(
            {"bold": True, "bg_color": "#e2e8f0", "border": 1}
        )
        for sheet_name, worksheet in writer.sheets.items():
            worksheet.set_zoom(90)
            worksheet.freeze_panes(1, 0)
            worksheet.set_row(0, 20, fmt_header)
    output.seek(0)
    return output


def export_pdf(
    df: pd.DataFrame,
    kpis: List[Dict[str, str]],
    charts: Iterable,
    template_path: Path,
    logo_path: Path,
    filtros: str,
    titulo: str = "Dashboard Centro Renal",
) -> bytes:
    template_dir = template_path.parent
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(),
    )
    template = env.get_template(template_path.name)
    chart_uris = [uri for uri in (_fig_to_uri(fig) for fig in charts) if uri]

    tabla = {
        "columns": ["Sede", "Persona", "Registros", "Días"],
        "rows": (
            df.groupby(["sede", "nombre"])
            .agg(registros=("tipo_registro", "count"), dias=("dias", "sum"))
            .reset_index()
            .values.tolist()
        )[:40],
    }
    html = template.render(
        titulo=titulo,
        emitido=datetime.now().strftime("%d/%m/%Y %H:%M"),
        rango=filtros,
        filtros=filtros,
        kpis=kpis,
        charts=chart_uris,
        tabla=tabla,
        logo_path=str(logo_path),
    )
    pdf_bytes = HTML(string=html, base_url=str(template_dir)).write_pdf()
    return pdf_bytes
