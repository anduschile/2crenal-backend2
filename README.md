# Dashboard Centro Renal SPA

Aplicacion multipagina (Streamlit) para monitorear personas, permisos, licencias y reportes del Centro Renal SPA. La interface replica el look & feel del panel **AndusChile**: sidebar con iconos, top bar con chips de filtro, tarjetas elevadas, graficas suaves (Plotly) y listas operativas (Permisos proximos, Licencias >15 dias, Turnos criticos). Toda la capa visual se centraliza en `.streamlit/config.toml`, `assets/styles.css` y helpers reutilizables (`components/ui.py`, `components/KpiCard.py`, `utils/colors.py`).

## Requisitos
- Python 3.10+
- pip / virtualenv recomendado

## Instalacion
```
cd crenal_dashboard
python -m venv .venv
.venv\Scripts\activate  # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecucion
```
streamlit run app.py
```
La aplicacion abre en http://localhost:8501. El sidebar permite elegir la fuente de datos (base interna `data/base_maestra.xlsx`, ejemplo o archivo cargado). Los filtros persisten mediante `st.session_state` + query params, por lo que recargar o compartir la URL mantiene el contexto.

## Navegacion
- **Inicio**: KPIs globales, tendencia mensual (area + barras), distribucion por sede/tipo y listas operativas (Permisos proximos, Licencias >15 dias, Turnos criticos).
- **00_Ayuda**: guia rapida y glosario.
- **01_Personas**: resumen maestro por funcionario (KPIs, charts en cards, tabla AgGrid con columnas ancladas).
- **02_Permisos**: bandeja con KPIs, tendencia mensual y top personas por dias/horas.
- **03_Licencias**: seguimiento de licencias medicas con alertas para casos >15 dias.
- **04_Reportes**: Export Builder (seleccion de columnas, CSV/XLSX/PDF, respeta filtros activos).
- **05_Config**: edicion de umbrales, equivalencias y mapeo de columnas (persisten en `config/config.yaml`).
- **06_Registro**: formulario para registrar y editar manualmente permisos/licencias/vacaciones. Elige un funcionario (autocompleta datos), define tipo/fechas y agrega observaciones. Desde la misma vista puedes editar o eliminar registros existentes; los cambios se sincronizan con la base activa.

## Estado de los datos
- Coloca la base oficial en `data/base_maestra.xlsx` (ignorada por git).
- `data/ejemplo_base.xlsx` contiene registros ficticios para pruebas.
- Evita subir datos sensibles; usa la carga local o un storage seguro.

## Exportaciones
- **CSV**: descarga inmediata del subconjunto filtrado.
- **XLSX**: utiliza `utils/exports.py` (detalle, resumen, pivotes y metricas de turnos).
- **PDF**: WeasyPrint + plantilla Jinja2 (`templates/reporte.html`); requiere dependencias GTK/Cairo segun SO.

## Estilo visual
- Tema claro inspirado en AndusChile: tipografia Inter/SF, sombras suaves, grilla de 8px y paleta fria (`utils/colors.py`).
- Sidebar personalizado con avatar, iconos HTML y CTA “Exportar CSV”.
- Top bar con chips de filtros (`filter_chips`) y acciones rapidas (boton Exportar).
- Tablas AgGrid heredan la gama cromatica (header gris, hover azul) y las graficas Plotly usan el mismo color set.

## Limpieza
`.gitignore` excluye `.venv/`, `__pycache__/`, `*.pyc`, `data/*.xlsx` y `.streamlit/credentials.toml` para evitar subir dependencias o datos reales.
