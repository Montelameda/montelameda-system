##### pages/agregar_producto.py  (versión unificada) #####
# -----------------------------------------------------------------------------
# Esta versión conserva el layout original (tabs, estilos, formulas de precios)
# e integra la pestaña "🛒 MercadoLibre" con autodetección de categoría y
# atributos obligatorios (cuando la API los devuelve).  Todo lo nuevo es plug‑in
# y no rompe tu lógica previa.
# -----------------------------------------------------------------------------

import streamlit as st
import datetime, math, requests

from login_app import login, esta_autenticado, obtener_rol
import firebase_config
import ml_api  # utilidades MercadoLibre

# ------------------ SEGURIDAD ------------------
if not esta_autenticado():
    login()
    st.stop()

if obtener_rol() != "admin":
    st.error("Acceso solo para administradores.")
    st.stop()

# ------------------ SETUP PÁGINA ---------------
st.set_page_config(page_title="Agregar producto", page_icon="➕", layout="wide")

if "ganancia_fb" not in st.session_state:
    st.session_state.update({
        "ganancia_fb": 0,
        "ganancia_ml": 0,
        "ml_cat_id": "",
        "ml_cat_name": "",
        "ml_attrs": {},
    })

st.title("➕ Agregar producto")

# ╔═════════════════════════════════════════════════════════════════╗
# ║ 1. IDENTIFICACIÓN                                              ║
# ╚═════════════════════════════════════════════════════════════════╝

tabs = st.tabs([
    "📑 Identificación",
    "🖼️ Visuales y Descripción",
    "💰 Precios",
    "📦 Stock y Opciones",
    "🛒 MercadoLibre",
])

# ------------------------------------------------------------------
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        codigo_barra = st.text_input("Código de barra *")
        estado       = st.selectbox("Estado *", ["Nuevo", "Usado"])
    with col2:
        codigo_min   = st.text_input("Código mínimo *")
        marca        = st.text_input("Marca *")
    with col3:
        titulo       = st.text_input("Nombre del producto *", key="nombre_prod")
        proveedor    = st.text_input("Proveedor *")

    categoria_fb = st.selectbox(
        "Categoría Facebook *",
        ["Arte y manualidades", "Juguetes", "Electrónica", "Hogar"],
        index=0
    )

# ╔═════════════════════════════════════════════════════════════════╗
# ║ 2. VISUALES Y DESCRIPCIÓN (se mantiene tu lógica)               ║
# ╚═════════════════════════════════════════════════════════════════╝

with tabs[1]:
    st.text_area("Descripción larga", height=120)
    st.file_uploader("Fotos (hasta 6)", type=["jpg", "png"], accept_multiple_files=True)

# ╔═════════════════════════════════════════════════════════════════╗
# ║ 3. PRECIOS (cálculo en vivo)                                   ║
# ╚═════════════════════════════════════════════════════════════════╝

def refrescar_precios():
    compra      = st.session_state.get("precio_compra", 0)
    fb_precio   = st.session_state.get("precio_fb", 0)
    fb_fee      = st.session_state.get("comision_fb", 0)
    ml_precio   = st.session_state.get("precio_ml", 0)
    ml_fee      = st.session_state.get("comision_ml", 0)
    ml_envio    = st.session_state.get("envio_ml", 0)

    st.session_state["ganancia_fb"] = fb_precio - compra - fb_fee
    st.session_state["ganancia_ml"] = ml_precio - compra - ml_fee - ml_envio

def money_input(label, key, **kwargs):
    return st.number_input(label, key=key, min_value=0.0, step=100.0,
                           format="%i", on_change=refrescar_precios, **kwargs)

with tabs[2]:
    precio_compra = money_input("Precio compra *", "precio_compra")

    colA, colB, colC = st.columns(3)
    with colA:
        st.subheader("💰 Facebook")
        precio_fb   = money_input("Precio", "precio_fb")
        com_fb      = money_input("Comisión vendedor", "comision_fb")
        st.text_input("Precio al por mayor x3", key="precio_mayor")
        st.markdown(f"Ganancia estimada: **${st.session_state['ganancia_fb']:,}**", unsafe_allow_html=True)

    with colB:
        st.subheader("💰 MercadoLibre")
        precio_ml  = money_input("Precio venta", "precio_ml")
        com_ml     = money_input("Comisión ML", "comision_ml")
        envio_ml   = money_input("Envío ML", "envio_ml")
        st.markdown(f"Ganancia estimada: **${st.session_state['ganancia_ml']:,}**", unsafe_allow_html=True)

    with colC:
        st.subheader("💰 ML -30 %")
        st.text_input("Precio -30 %", key="precio_ml_desc")
        st.text_input("Comisión", key="ml_desc_fee")
        st.text_input("Envío", key="ml_desc_envio")

# ╔═════════════════════════════════════════════════════════════════╗
# ║ 4. STOCK Y OPCIONES (placeholder)                               ║
# ╚═════════════════════════════════════════════════════════════════╝

with tabs[3]:
    st.number_input("Stock inicial", min_value=0, step=1)
    st.text_input("Variantes (color, talla, etc.)")

# ╔═════════════════════════════════════════════════════════════════╗
# ║ 5. MERCADOLIBRE                                                ║
# ╚═════════════════════════════════════════════════════════════════╝

with tabs[4]:
    # --- Autodetección de categoría ---
    sugerencias = ml_api.suggest_categories(titulo) if titulo else []

    if sugerencias:
        nombres   = [n for _, n in sugerencias]
        default   = 0
        choice    = st.selectbox("Categoría sugerida", nombres, index=default)
        ml_cat_id, ml_cat_name = sugerencias[nombres.index(choice)]
    else:
        st.warning("La API de ML no devolvió categorías. Escribe un nombre más específico.")
        ml_cat_id = st.text_input("ID categoría ML", value="")
        ml_cat_name = ""

    st.text_input("ID categoría ML", value=ml_cat_id, disabled=True)

    # --- Atributos obligatorios ---
    attrs = ml_api.get_required_attrs(ml_cat_id)
    ml_attrs = {}

    if attrs:
        st.subheader("Campos obligatorios")
        for att in attrs:
            aid, label = att["id"], att["name"]
            vtype = att["value_type"]
            if vtype in ("list", "boolean"):
                opts = [v["name"] for v in att.get("values", [])] or ["Sí", "No"]
                ml_attrs[aid] = st.selectbox(label, opts, key=f"ml_{aid}")
            else:
                ml_attrs[aid] = st.text_input(label, key=f"ml_{aid}")
    else:
        st.info("Sin atributos obligatorios para esta categoría o la API está bloqueada.")

# ---------------------- GUARDAR ----------------------

if st.button("Agregar Producto", type="primary"):
    doc = {
        "codigo_barra": codigo_barra,
        "codigo_min": codigo_min,
        "titulo": titulo,
        "estado": estado,
        "marca": marca,
        "proveedor": proveedor,
        "categoria_fb": categoria_fb,
        "precio_compra": precio_compra,
        "precio_fb": precio_fb,
        "comision_fb": com_fb,
        "precio_ml": precio_ml,
        "comision_ml": com_ml,
        "envio_ml": envio_ml,
        "ganancia_fb": st.session_state["ganancia_fb"],
        "ganancia_ml": st.session_state["ganancia_ml"],
        # ---- MercadoLibre ----
        "ml_cat_id": ml_cat_id,
        "ml_cat_name": ml_cat_name,
        "ml_attrs": ml_attrs,
        # ---- metadatos ----
        "creado": datetime.datetime.utcnow(),
    }
    firebase_config.db.collection("productos").add(doc)
    st.success("Producto agregado correctamente ✅")
