
# pages/agregar_producto.py  – versión estable 18‑Jun‑2025
# ---------------------------------------------------------------------
# Conserva tu interfaz original con pestañas:
# Identificación | Visuales y Descripción | Precios | Stock y Opciones | MercadoLibre
# + Fórmulas en vivo para Facebook y MercadoLibre + Auto‑categoría ML.
# ---------------------------------------------------------------------

import streamlit as st
import requests, datetime, math
import ml_api  # tu helper recién creado
from firebase_config import db
from login_app import login, esta_autenticado, obtener_rol

# ---------------- Seguridad ----------------
if not esta_autenticado():
    login()
    st.stop()

if obtener_rol() != "admin":
    st.error("Acceso solo para administradores")
    st.stop()

st.set_page_config(page_title="Agregar Producto")
st.title("➕ Agregar producto")

# ---------------- Formulario ----------------
tabs = st.tabs(
    ["📑 Identificación",
     "🖼️ Visuales y Descripción",
     "💰 Precios",
     "📦 Stock y Opciones",
     "🛒 MercadoLibre"]
)

# --- Identificación ---
with tabs[0]:
    codigo_barras   = st.text_input("Código de barra *")
    nombre_producto = st.text_input("Nombre del producto *")
    marca           = st.text_input("Marca *")
    categoria_fb    = st.selectbox("Categoría Facebook *", ["Arte y manualidades", "Juguetes", "Otros"])
    proveedor       = st.selectbox("Proveedor *", ["ABC", "XYZ"])

# --- Visuales & Descripción ---
with tabs[1]:
    descripcion = st.text_area("Descripción")
    st.file_uploader("Imagen principal", type=["png", "jpg"])

# ---------- Función de cálculo de precios ----------
def calcular_precios():
    compra      = int(st.session_state.get("precio_compra", 0))
    venta_fb    = int(st.session_state.get("precio_fb", 0))
    comision_fb = int(st.session_state.get("comision_fb", 0))

    venta_ml    = int(st.session_state.get("precio_ml", 0))
    comision_ml = int(st.session_state.get("comision_ml", 0))
    envio_ml    = int(st.session_state.get("envio_ml", 0))

    st.session_state["ganancia_fb"] = max(venta_fb - compra - comision_fb, 0)
    st.session_state["ganancia_ml"] = max(venta_ml - compra - comision_ml - envio_ml, 0)

# --- Precios ---
with tabs[2]:
    st.number_input("Precio compra *", min_value=0, format="%i", key="precio_compra", on_change=calcular_precios)

    col_fb, col_ml, col_ml30 = st.columns(3)
    with col_fb:
        st.markdown("### 💸 Facebook")
        st.number_input("Precio",         min_value=0, format="%i", key="precio_fb",    on_change=calcular_precios)
        st.number_input("Comisión vendedor", min_value=0, format="%i", key="comision_fb", on_change=calcular_precios)
        st.number_input("Precio al por mayor x3", min_value=0, format="%i", key="precio_mayor", step=1)

        st.markdown(f"Ganancia estimada FB: **${{st.session_state.get('ganancia_fb',0):,}}**")

    with col_ml:
        st.markdown("### 💸 MercadoLibre")
        st.number_input("Precio venta", min_value=0, format="%i", key="precio_ml", on_change=calcular_precios)
        st.number_input("Comisión ML",  min_value=0, format="%i", key="comision_ml", on_change=calcular_precios)
        st.number_input("Envío ML",     min_value=0, format="%i", key="envio_ml", on_change=calcular_precios)
        st.markdown(f"Ganancia estimada ML: **${{st.session_state.get('ganancia_ml',0):,}}**")

    with col_ml30:
        st.markdown("### 💸 ML -30 %")
        st.text_input("Precio -30 %",  value=st.session_state.get("precio_ml", 0), disabled=True, key="precio_ml30_display")

# --- Stock y Opciones ---
with tabs[3]:
    stock = st.number_input("Stock inicial", min_value=0, format="%i")

# --- MercadoLibre ---
with tabs[4]:
    st.markdown("### 🛒 MercadoLibre")

    # Auto‑categoría
    if nombre_producto:
        sugerencias = ml_api.suggest_categories(nombre_producto)
    else:
        sugerencias = []

    opc_display = [n for _, n in sugerencias] or ["(sin sugerencias)"]
    categoria_seleccionada = st.selectbox("Categoría sugerida", opc_display)
    ml_cat_id = sugest_id = ""
    if sugerencias:
        ml_cat_id, _ = sugerencias[opc_display.index(categoria_seleccionada)]

    st.text_input("ID categoría ML", value=ml_cat_id, disabled=True, key="ml_cat_id_display")

    # Atributos obligatorios
    ml_attrs = {}
    if ml_cat_id:
        for att in ml_api.get_required_attrs(ml_cat_id):
            aid, label = att["id"], att["name"]
            if att["value_type"] in ("list", "boolean"):
                opts = [v["name"] for v in att.get("values", [])] or ["Sí", "No"]
                ml_attrs[aid] = st.selectbox(label, opts, key=f"ml_{aid}")
            else:
                ml_attrs[aid] = st.text_input(label, key=f"ml_{aid}")

# ---------- Guardar ----------
if st.button("Agregar Producto"):
    calcular_precios()  # asegura valores actuales
    doc = {
        "titulo": nombre_producto,
        "marca": marca,
        "categoria_fb": categoria_fb,
        "proveedor": proveedor,
        "ml_cat_id": ml_cat_id,
        "ml_attrs": ml_attrs,
        "precio_compra": st.session_state.get("precio_compra", 0),
        "precio_fb": st.session_state.get("precio_fb", 0),
        "precio_ml": st.session_state.get("precio_ml", 0),
        "ganancia_fb": st.session_state.get("ganancia_fb", 0),
        "ganancia_ml": st.session_state.get("ganancia_ml", 0),
        "fecha_creacion": datetime.datetime.utcnow().isoformat()
    }
    db.collection("productos").add(doc)
    st.success("Producto guardado 🙌")
