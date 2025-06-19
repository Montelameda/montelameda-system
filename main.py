
import os
import sys
import streamlit as st
import pandas as pd
from io import BytesIO

sys.path.append(os.path.join(os.path.dirname(__file__), "modulos"))
from login_app import login, esta_autenticado, obtener_rol
import firebase_config

if not esta_autenticado():
    login()
    st.stop()
rol_usuario = obtener_rol()

st.set_page_config(page_title="MonteLameda System", layout="wide")

# Código omitido por brevedad (CSS, encabezado, favicon)

PRODUCTOS_POR_PAGINA = 20
if "pagina_actual" not in st.session_state:
    st.session_state["pagina_actual"] = 0
if "productos_seleccionados" not in st.session_state:
    st.session_state["productos_seleccionados"] = []

pagina = st.session_state["pagina_actual"]

todos_productos = [doc.to_dict() | {"doc_id": doc.id}
                   for doc in firebase_config.db.collection("productos").stream()]

busq_col, orden_col = st.columns([3.5, 2])
with busq_col:
    texto_busqueda = st.text_input("🔍 Buscar producto...", key="busqueda_nombre")
with orden_col:
    orden = st.selectbox("Ordenar por", ["Más reciente", "Precio más bajo", "Precio más alto"])

if st.session_state.get("ultima_busqueda", "") != texto_busqueda:
    st.session_state["pagina_actual"] = 0
    st.session_state["ultima_busqueda"] = texto_busqueda
    pagina = 0

productos_filtrados = [p for p in todos_productos
                       if texto_busqueda.lower() in p.get("nombre_producto", "").lower()]                        if texto_busqueda.strip() else todos_productos

campo_orden, asc = "id", False
if orden == "Precio más bajo":
    campo_orden, asc = "precio_facebook", True
elif orden == "Precio más alto":
    campo_orden, asc = "precio_facebook", False

productos_filtrados.sort(key=lambda x: x.get(campo_orden, 0), reverse=not asc)
productos = productos_filtrados[pagina * PRODUCTOS_POR_PAGINA:(pagina + 1) * PRODUCTOS_POR_PAGINA]

def render_tarjeta_producto(prod):
    img_url = prod.get('imagen_principal_url', 'https://cdn-icons-png.flaticon.com/512/1828/1828884.png')
    nombre  = prod.get('nombre_producto', 'Sin nombre')
    precio  = prod.get('precio_facebook', 'N/A')
    doc_id  = prod['doc_id']

    seleccionado = st.checkbox("Seleccionar", key=f"select_{doc_id}",
                               value=doc_id in st.session_state["productos_seleccionados"])
    if seleccionado and doc_id not in st.session_state["productos_seleccionados"]:
        st.session_state["productos_seleccionados"].append(doc_id)
    elif not seleccionado and doc_id in st.session_state["productos_seleccionados"]:
        st.session_state["productos_seleccionados"].remove(doc_id)

    st.markdown(f"<div>{nombre} - ${precio}</div>", unsafe_allow_html=True)

    col_det, col_ml = st.columns(2, gap="small")
    with col_det:
        if st.button("👁️‍🗨️ Ver detalles", key=f"detalle_{doc_id}"):
            st.session_state["producto_actual"] = doc_id
            st.switch_page("ver_producto")
    with col_ml:
        if st.button("🛒 Publicar ML", key=f"ml_{doc_id}"):
            st.query_params["id"] = doc_id
            st.switch_page("pages/2_Mercado_Libre.py")

if productos:
    cols = st.columns(4)
    for idx, prod in enumerate(productos):
        with cols[idx % 4]:
            render_tarjeta_producto(prod)
else:
    st.warning("No hay productos para mostrar.")
