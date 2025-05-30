
import streamlit as st
import sys
import os
import re

from login_app import login, esta_autenticado, obtener_rol

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "modulos"))
import firebase_config

import requests
from PIL import Image
from io import BytesIO
import zipfile

# --- Autenticación ---
if not esta_autenticado():
    login()
    st.stop()

rol = obtener_rol()

st.set_page_config(page_title="Detalle del Producto", layout="centered")

producto_id = st.session_state.get("producto_actual")
if not producto_id:
    st.error("❌ No se proporcionó un ID de producto válido.")
    st.stop()

if "last_producto_id" not in st.session_state or st.session_state.last_producto_id != producto_id:
    st.session_state.img_selected = 0
    st.session_state.last_producto_id = producto_id

db = firebase_config.db
doc_ref = db.collection("productos").document(producto_id)
doc = doc_ref.get()
if not doc.exists:
    st.error("⚠️ El producto no fue encontrado en la base de datos.")
    st.stop()
producto = doc.to_dict()

def tiene_valor(x):
    if x is None:
        return False
    if isinstance(x, (list, dict)):
        return len(x) > 0
    return str(x).strip() != ""

# ---- BOTONES ARRIBA ----
colbtn1, colbtn2, colbtn3 = st.columns([1,1,1], gap="medium")
with colbtn1:
    if st.button("⬅️ Volver al catálogo"):
        st.session_state["go_to"] = "catalogo"
        st.rerun()
with colbtn2:
    if st.button("✏️ Editar producto"):
        st.query_params["producto_id"] = producto_id
        st.switch_page("pages/editar_producto.py")

def exportar_producto(producto):
    titulo = producto.get("nombre_producto", "Sin_titulo")
    precio_fb = producto.get("precio_facebook", "Sin_precio")
    descripcion = producto.get("descripcion", "Sin_descripcion")
    etiquetas = producto.get("etiquetas", "Sin_etiquetas")

    texto_info = f"""TÍTULO: {titulo}
PRECIO FACEBOOK: {precio_fb}
DESCRIPCIÓN:
{descripcion}

ETIQUETAS:
{etiquetas}
"""

    urls = []
    if producto.get("imagen_principal_url"):
        urls.append(producto["imagen_principal_url"])
    if producto.get("imagenes_secundarias_url"):
        urls += [u.strip() for u in str(producto["imagenes_secundarias_url"]).split(",") if u.strip()]

    zip_buffer = BytesIO()
    errores = []
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("info.txt", texto_info)
        for idx, url in enumerate(urls):
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                img = Image.open(BytesIO(r.content))
                ext = img.format.lower() if img.format else "jpg"
                zip_file.writestr(f"imagen_{idx+1}.{ext}", r.content)
            except Exception as e:
                errores.append(f"Error con {url}: {e}")

    return zip_buffer.getvalue(), titulo, errores

with colbtn3:
    zip_data, nombre_zip, errores = exportar_producto(producto)
    if errores:
        st.warning("Algunas imágenes no se pudieron descargar:\n\n" + "\n".join(errores))

    nombre_seguro = re.sub(r'[^\w\-_.]', '_', nombre_zip)
    zip_buffer = BytesIO(zip_data)

    st.download_button(
        label="⬇️ Exportar ZIP",
        data=zip_buffer.getvalue(),
        file_name=f"{nombre_seguro}.zip",
        mime="application/zip"
    )
