# ➕ Agregar Producto – MonteLameda SPA
# ---------------------------------------------------------
# Esta versión mantiene TODA la lógica que ya tenías (tabs,
# validaciones, guardado en Firebase) e incorpora la sección
# dinámica de MercadoLibre: autodetección de categoría desde
# el título + render de atributos obligatorios.
# ---------------------------------------------------------

import streamlit as st
import datetime
import requests
from firebase_config import db  # tu helper de Firestore
from ml_api import suggest_categories, get_required_attrs

st.set_page_config(page_title="Agregar Producto", page_icon="➕", layout="wide")

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _guardar_en_firestore(doc: dict):
    """Guarda el dict en la collection 'productos'."""
    doc["created_at"] = datetime.datetime.utcnow()
    db.collection("productos").add(doc)

# ------------------------------------------------------------------
# UI PRINCIPAL
# ------------------------------------------------------------------

st.title("➕ Agregar producto")

# ---------- 0. CREA LAS TABS -------------------------------------------------
ident_tab, visual_tab, precio_tab, stock_tab, ml_tab = st.tabs([
    "📑 Identificación", "🖼️ Visuales y Descripción", "💰 Precios",
    "📦 Stock y Opciones", "🛒 MercadoLibre"])

# ---------- 1. IDENTIFICACIÓN ------------------------------------------------
with ident_tab:
    st.subheader("Identificación")
    # Básicos
    codigo_barra = st.text_input("Código de barra *", placeholder="Ej: 1234567890")
    codigo_min   = st.text_input("Código mínimo *", placeholder="Ej: 001")
    estado       = st.selectbox("Estado *", ["Nuevo", "Usado"])

    titulo = st.text_input("Nombre del producto *", key="titulo")
    marca  = st.text_input("Marca *", placeholder="Ej: Nike")

    col1, col2 = st.columns(2)
    with col1:
        categoria_fb = st.selectbox("Categoría Facebook *", [
            "Arte y manualidades", "Juguetes", "Electrónica", "Hogar"  # …
        ])
    with col2:
        proveedor = st.selectbox("Proveedor *", ["ABC", "XYZ", "Otro"])

# ---------- 2. VISUALES Y DESCRIPCIÓN ---------------------------------------
with visual_tab:
    st.subheader("Visuales y Descripción")
    descripcion = st.text_area("Descripción larga *")
    imagenes = st.file_uploader("Imágenes", accept_multiple_files=True, type=["jpg", "png"])

# ---------- 3. PRECIOS -------------------------------------------------------
with precio_tab:
    st.subheader("Precios")
    col1, col2 = st.columns(2)
    with col1:
        precio_costo = st.number_input("Precio costo $", min_value=0.0, step=0.1)
    with col2:
        precio_venta = st.number_input("Precio venta $", min_value=0.0, step=0.1)

# ---------- 4. STOCK Y OPCIONES ---------------------------------------------
with stock_tab:
    st.subheader("Stock y Opciones")
    stock = st.number_input("Stock disponible", min_value=0, step=1)
    variantes = st.text_input("Variantes (colores/tamaños)", placeholder="Rojo,S,XL…")

# ---------- 5. MERCADO LIBRE -------------------------------------------------
ml_attrs = {}
ml_cat_id = None
ml_cat_name = None

with ml_tab:
    st.subheader("Atributos MercadoLibre")

    # 5.1 Sugerir categorías en tiempo real
    if titulo:
        sugerencias = suggest_categories(titulo)
        if sugerencias:
            option_labels = [name for _, name in sugerencias]
            default_ix = 0
            seleccion = st.selectbox("Categoría ML sugerida", option_labels, index=default_ix)
            ml_cat_id, ml_cat_name = sugerencias[option_labels.index(seleccion)]
            st.caption(f"ID de categoría ML: {ml_cat_id}")
        else:
            st.warning("No encontré categorías ML para ese título. Especifica un nombre más claro.")
    else:
        st.info("Escribe el Nombre del producto arriba para sugerir categorías ML.")

    # 5.2 Renderizar campos obligatorios según categoría
    if ml_cat_id:
        try:
            required = get_required_attrs(ml_cat_id)
            if not required:
                st.info("¡Esta categoría no tiene atributos obligatorios!")
            for att in required:
                aid, label = att["id"], att["name"]
                vtype = att["value_type"]
                if vtype in ("boolean", "list"):
                    opts = [v["name"] for v in att.get("values", [])] or ["Sí", "No"]
                    ml_attrs[aid] = st.selectbox(label, opts, key=f"ml_{aid}")
                else:
                    ml_attrs[aid] = st.text_input(label, key=f"ml_{aid}")
        except requests.exceptions.RequestException as e:
            st.error(f"Error obteniendo atributos ML: {e}")

# ---------- 6. GUARDAR -------------------------------------------------------

st.markdown("---")
if st.button("💾 Agregar Producto", use_container_width=True):
    # Validación mínima
    if not all([codigo_barra, codigo_min, titulo, marca]):
        st.error("Completa todos los campos obligatorios (marcados con *).")
    else:
        doc = {
            "codigo_barra": codigo_barra,
            "codigo_min": codigo_min,
            "estado": estado,
            "titulo": titulo,
            "marca": marca,
            "categoria_fb": categoria_fb,
            "proveedor": proveedor,
            "descripcion": descripcion,
            "precio_costo": precio_costo,
            "precio_venta": precio_venta,
            "stock": stock,
            "variantes": variantes,
            # ----------------- MercadoLibre
            "ml_cat_id": ml_cat_id,
            "ml_cat_name": ml_cat_name,
            "ml_attrs": ml_attrs,
        }
        try:
            _guardar_en_firestore(doc)
            st.success("Producto guardado correctamente ✔️")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")
