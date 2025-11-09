from __future__ import annotations

import copy

import streamlit as st
import yaml

from app import CONFIG_PATH, use_app_shell
from components import render_empty_state


def main():
    use_app_shell("Configuración", "Configuración / Preferencias", active_page="Config", compact_sidebar=True)
    if "config" not in st.session_state:
        render_empty_state(
            "Sin configuración",
            "Reinicia la aplicación para volver a cargar config.yaml.",
        )
        return

    current = copy.deepcopy(st.session_state["config"])
    with st.form("config-form"):
        st.subheader("Umbrales de semáforo")
        for nombre, valores in current.get("umbrales", {}).items():
            col1, col2 = st.columns(2)
            valores["verde"] = col1.number_input(f"{nombre} · Verde", value=float(valores.get("verde", 0.0)))
            valores["amarillo"] = col2.number_input(f"{nombre} · Amarillo", value=float(valores.get("amarillo", 0.0)))

        st.subheader("Equivalencias de sedes")
        for clave, valor in current.get("sede_equivalencias", {}).items():
            current["sede_equivalencias"][clave] = st.text_input(clave, value=valor)

        st.subheader("Mapeo de columnas")
        for campo, ref in current.get("column_mapping", {}).items():
            current["column_mapping"][campo] = st.text_input(campo, value=ref)

        submitted = st.form_submit_button("Guardar cambios")
        if submitted:
            with CONFIG_PATH.open("w", encoding="utf-8") as fh:
                yaml.safe_dump(current, fh, allow_unicode=True)
            st.session_state["config"] = copy.deepcopy(current)
            st.success("Configuración actualizada")

    if st.button("Restablecer valores por defecto", type="secondary"):
        st.session_state["config"] = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        st.success("Config restablecida. Recarga la página para ver los cambios.")


if __name__ == "__main__":
    main()
