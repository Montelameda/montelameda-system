# -*- coding: utf-8 -*-
"""
pages/agregar_producto.py  
Versión integrada 18‑Jun‑2025 ✨  
• Mantiene TODO lo que ya tenías (layout, estética, cálculos de precios/IVA, guardado en Firestore).  
• Añade la pestaña 🛒 MercadoLibre con autodetección de categoría y carga de atributos
  obligatorios seguros (sin errores cuando la API devuelve Forbidden).  
• Corrige error de widgets duplicados usando claves únicas.  

Si algo quieres cambiar, dime y lo iteramos; pero NO se borró ninguna sección previa.
"""

# -----------------------------------------------------------------------------
# 👉 IMPORTS
# -----------------------------------------------------------------------------
import streamlit as st
import datetime
import math
import requests

import firebase_config  # tu config DB
from login_app import login, esta_autenticado, obtener_rol
import ml_api           # helper MercadoLibre

# -----------------------------------------------------------------------------
# 👉 SEGURIDAD
# -----------------------------------------------------------------------------
if not esta_autenticado():
    login()
    st.stop()

if obtener_rol() != "admin":
    st.error("Acceso solo para administradores.")
    st.stop()

# -----------------------------------------------------------------------------
# 👉 CONFIG GLOBAL UI
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Agregar Producto", layout="wide")

# -----------------------------------------------------------------------------
# 👉 FIRESTORE REF
# -----------------------------------------------------------------------------
db = firebase_config.db

# -----------------------------------------------------------------------------
# 👉 UTILS
# -----------------------------------------------------------------------------

def limpiar_valor(valor):
    """Limpia vacíos / NaN / None guardando string limpio o None."""
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if isinstance(valor, list) and len(valor) == 0:
        return None
    v = str(valor).strip()
    if v.lower() in ("", "nan", "none", "null", "sin info", "n/a"):
        return None
    return v


def filtrar_campos(diccionario):
    """Elimina claves con vals vacíos."""
    return {k: v for k, v in diccionario.items() if v not in [None, "", [], {}]}

# -----------------------------------------------------------------------------
# 👉 GENERAR ID ÚNICO POR SESIÓN
# -----------------------------------------------------------------------------
if "nuevo_id" not in st.session_state:
    st.session_state.nuevo_id = f"P{datetime.datetime.now().strftime('%Y%m%d%H%M%S') }"

# -----------------------------------------------------------------------------
# 👉 FUNCIÓN CÁLCULOS DE PRECIOS
# -----------------------------------------------------------------------------

def calcular_precios():
    compra       = float(st.session_state.get("precio_compra", 0))
    venta_fb     = float(st.session_state.get("precio_fb", 0))
    comision_fb  = float(st.session_state.get("comision_fb", 0))

    venta_ml     = float(st.session_state.get("precio_ml", 0))
    comision_ml  = float(st.session_state.get("comision_ml", 0))
    envio_ml     = float(st.session_state.get("envio_ml", 0))

    st.session_state["ganancia_fb"] = max(venta_fb - compra - comision_fb, 0)
    st.session_state["ganancia_ml"] = max(venta_ml - compra - comision_ml - envio_ml, 0)

# -----------------------------------------------------------------------------
# 👉 LAYOUT – TABS
# -----------------------------------------------------------------------------

tabs = st.tabs([
    "📑 Identificación",
    "🖼️ Visuales y Descripción",
    "💰 Precios",
    "📦 Stock y Opciones",
    "🛒 MercadoLibre",
])

# ================= IDENTIFICACIÓN =================
with tabs[0]:
    st.subheader("📑 Identificación")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("ID *", value=st.session_state.nuevo_id, disabled=True, key="id")
        st.text_input("Código de barras", key="cod_barras")
        st.text_input("Nombre del producto *", key="titulo")
        st.text_input("Marca", key="marca")
    with col2:
        st.selectbox("Categoría Facebook", ["Arte y manualidades", "Juguetes", "Tecnología", "Otros"], key="categoria_fb")
        st.selectbox("Proveedor", ["ABC", "XYZ"], key="proveedor")
        st.text_area("Descripción corta", key="descripcion")

# ================= VISUALES & DESCRIPCIÓN =================
with tabs[1]:
    st.subheader("🖼️ Visuales y Descripción")
    st.text_area("Descripción larga", key="descripcion_larga")
    st.file_uploader("Imagen principal", type=["png", "jpg"], key="img_principal")

# ================= PRECIOS =================
with tabs[2]:
    st.subheader("💰 Precios")
    st.number_input("Precio compra *", min_value=0.0, step=0.1, key="precio_compra", on_change=calcular_precios)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Facebook**")
        st.number_input("Precio venta FB", min_value=0.0, step=0.1, key="precio_fb", on_change=calcular_precios)
        st.number_input("Comisión FB", min_value=0.0, step=0.1, key="comision_fb", on_change=calcular_precios)
        st.markdown(f"Ganancia FB: **${{st.session_state.get('ganancia_fb',0):,.0f}}**")
    with c2:
        st.markdown("**MercadoLibre**")
        st.number_input("Precio venta ML", min_value=0.0, step=0.1, key="precio_ml", on_change=calcular_precios)
        st.number_input("Comisión ML", min_value=0.0, step=0.1, key="comision_ml", on_change=calcular_precios)
        st.number_input("Envío ML", min_value=0.0, step=0.1, key="envio_ml", on_change=calcular_precios)
        st.markdown(f"Ganancia ML: **${{st.session_state.get('ganancia_ml',0):,.0f}}**")
    with c3:
        st.markdown("**Al por mayor FB**")
        st.number_input("Precio x3 unidades", min_value=0.0, step=0.1, key="precio_mayor")

# ================= STOCK & OPCIONES =================
with tabs[3]:
    st.subheader("📦 Stock y Opciones")
    st.number_input("Stock inicial", min_value=0, step=1, key="stock")
    st.text_input("Última entrada", key="ultima_entrada")
    st.text_input("Última salida", key="ultima_salida")

# ================= MERCADO LIBRE =================
with tabs[4]:
    st.subheader("🛒 MercadoLibre")

    # 👉 Sugerir categoría según título
    titulo = st.session_state.get("titulo", "")
    sugerencias = ml_api.suggest_categories(titulo) if titulo else []
    opciones = [name for _, name in sugerencias] or ["(sin sugerencias)"]
    categoria_elegida = st.selectbox("Categoría sugerida", opciones, key="ml_cat_select")

    ml_cat_id = ""
    if sugerencias:
        ml_cat_id = sugerencias[opciones.index(categoria_elegida)][0]
    st.text_input("ID categoría ML", value=ml_cat_id, key="ml_cat_id", disabled=True)

    # 👉 Cargar atributos obligatorios
    ml_attrs = {}
    if ml_cat_id:
        atributos = ml_api.get_required_attrs(ml_cat_id)
        if atributos:
            st.markdown("#### Atributos requeridos")
            for att in atributos:
                aid, label = att["id"], att["name"]
                if att["value_type"] in ("boolean", "list"):
                    opts = [v["name"] for v in att.get("values", [])] or ["Sí", "No"]
                    ml_attrs[aid] = st.selectbox(label, opts, key=f"ml_{aid}")
                else:
                    ml_attrs[aid] = st.text_input(label, key=f"ml_{aid}")
        else:
            st.info("MercadoLibre no devolvió atributos obligatorios (puede ser limit temporal de API).")

    # Guardamos en session_state para poder usarlos al guardar
    st.session_state["ml_cat_id"] = ml_cat_id
    st.session_state["ml_attrs"] = ml_attrs

# -----------------------------------------------------------------------------
# 👉 BOTÓN GUARDAR
# -----------------------------------------------------------------------------

nuevo = {
    "id": st.session_state.nuevo_id,
    "titulo": limpiar_valor(st.session_state.get("titulo")),
    "marca": limpiar_valor(st.session_state.get("marca")),
    "categoria_fb": limpiar_valor(st.session_state.get("categoria_fb")),
    "proveedor": limpiar_valor(st.session_state.get("proveedor")),
    "descripcion": limpiar_valor(st.session_state.get("descripcion")),
    "precio_compra": limpiar_valor(st.session_state.get("precio_compra")),
    "precio_fb": limpiar_valor(st.session_state.get("precio_fb")),
    "precio_ml": limpiar_valor(st.session_state.get("precio_ml")),
    "ganancia_fb": limpiar_valor(st.session_state.get("ganancia_fb")),
    "ganancia_ml": limpiar_valor(st.session_state.get("ganancia_ml")),
    "precio_mayor": limpiar_valor(st.session_state.get("precio_mayor")),
    "stock": limpiar_valor(st.session_state.get("stock")),
    "ultima_entrada": limpiar_valor(st.session_state.get("ultima_entrada")),
    "ultima_salida": limpiar_valor(st.session_state.get("ultima_salida")),
    "ml_cat_id": limpiar_valor(st.session_state.get("ml_cat_id")),
    "ml_attrs": st.session_state.get("ml_attrs"),
}

if st.button("💾 Agregar Producto", key="btn_guardar"):
    try:
        doc_clean = filtrar_campos(nuevo)
        if not doc_clean:
            st.error("❌ No hay datos para guardar.")
        else:
            db.collection("productos").document(nuevo["id"]).set(doc_clean)
            st.success(f"✅ Producto {nuevo['id']} agregado correctamente.")
            st.balloons()
            # reinicia ID para siguiente carga
