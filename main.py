import streamlit as st
import sys, os
import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), "modulos"))
from login_app import login, esta_autenticado, obtener_rol
import firebase_config

# --- Autenticación ---
if not esta_autenticado():
    login()
    st.stop()
rol_usuario = obtener_rol()  # "admin" o "vendedor"

# Configuración de la página
st.set_page_config(page_title="MonteLameda System", layout="wide")

# --- CSS Global ---
st.markdown("""
    <style>
    div.stButton > button {
        background: linear-gradient(90deg, #2062d8 80%, #1545a7 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 14px 0 !important;
        width: 100% !important;
        font-size: 1.09rem !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        box-shadow: 0 2px 8px rgba(32,98,216,0.10) !important;
        letter-spacing: 0.04em !important;
        outline: none !important;
        margin-top: 8px !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #1545a7 80%, #2062d8 100%) !important;
        color: #fff !important;
        letter-spacing: 0.08em !important;
        transform: scale(1.04) !important;
        box-shadow: 0 2px 16px #185cc9bb !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Encabezado y Logo ---
st.markdown("""
    <div style="display: flex; align-items: center; gap: 22px; margin: 8px 0 6px 0;">
        <img src="https://res.cloudinary.com/dkl4xbslu/image/upload/v1747363106/ChatGPT_Image_15_may_2025_22_37_31-Photoroom_yw4hqn.png" style="height:60px; width:60px; border-radius:50%; box-shadow:0 2px 16px #e0e0e0;" alt="Logo MonteLameda"/>
        <div style="flex-direction: column;">
            <span style="font-size: 2.05rem; font-weight: 900; color: #205ec5;">MonteLameda <span style='color:#1545a7;font-weight:800;'>Catálogo</span></span>
            <span style="color: #5a5a5a; font-size:1.08rem;">Gestión de productos y stock interno.</span>
        </div>
    </div>
    <hr style="border-top: 1.8px solid #f2f4f9;">
""", unsafe_allow_html=True)

# --- Favicon ---
st.markdown("""
    <link rel="icon" href="https://res.cloudinary.com/dkl4xbslu/image/upload/v1747363106/ChatGPT_Image_15_may_2025_22_37_31-Photoroom_yw4hqn.png" type="image/png" sizes="32x32">
""", unsafe_allow_html=True)

# --- Funciones para el banner ---
def obtener_banner_vendedor():
    doc = firebase_config.db.collection("config").document("banner_vendedor").get()
    return doc.to_dict().get("texto", "") if doc.exists else ""

def actualizar_banner_vendedor(nuevo_texto):
    firebase_config.db.collection("config").document("banner_vendedor").set({"texto": nuevo_texto})

# --- Banner editable para admin ---
if rol_usuario == "admin":
    with st.expander("Editar banner de vendedores (opcional)", expanded=False):
        texto_actual = obtener_banner_vendedor()
        nuevo_texto = st.text_area("Texto del banner (puedes usar emojis y HTML simple)", texto_actual, height=70, key="banner_admin")
        if st.button("Actualizar banner"):
            actualizar_banner_vendedor(nuevo_texto)
            st.success("Banner actualizado correctamente.")

# --- Banner visible para vendedores ---
if rol_usuario == "vendedor":
    banner_texto = obtener_banner_vendedor()
    if banner_texto.strip():
        st.markdown(f"""
            <div style="background:linear-gradient(90deg,#1545a7 60%,#1aa1ff 100%); color:#fff; padding:10px; border-radius:0 0 18px 18px; box-shadow:0 2px 14px #0002; margin-bottom: 18px; font-weight: 600; font-size:1.09rem; text-align:center;">
                {banner_texto} &nbsp; <span style="font-weight:400;">({datetime.datetime.now().strftime('%d-%m-%Y %H:%M')})</span>
            </div>
        """, unsafe_allow_html=True)

# --- CSS para tarjetas ---
st.markdown("""
    <style>
    .product-card-pro {
        background: #fff;
        border-radius: 16px;
        box-shadow: 0 2px 18px rgba(60,60,60,0.09), 0 1.5px 6px rgba(32,98,216,0.03);
        padding: 20px 14px;
        min-height: 410px;
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-bottom: 18px;
        transition: all 0.19s cubic-bezier(.4,2,.6,1);
    }
    .product-card-pro:hover {
        box-shadow: 0 4px 28px rgba(60,60,60,0.15), 0 1.5px 12px rgba(32,98,216,0.06);
        transform: translateY(-8px) scale(1.027);
        border: 2.5px solid #205ec5;
    }
    .product-title {
        font-weight: 700;
        font-size: 1.18rem;
        margin-bottom: 9px;
        color: #1b2537;
        text-align: center;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    </style>
""", unsafe_allow_html=True)

# --- Parámetros de paginación ---
PRODUCTOS_POR_PAGINA = 20
if "pagina_actual" not in st.session_state:
    st.session_state["pagina_actual"] = 0

pagina = st.session_state["pagina_actual"]

# --- Carga de productos ---
todos_productos = [doc.to_dict() | {"doc_id": doc.id} for doc in firebase_config.db.collection("productos").stream()]

# --- Barra de búsqueda y orden ---
busq_col, orden_col = st.columns([3.5, 2])
with busq_col:
    texto_busqueda = st.text_input("🔍 Buscar producto...", key="busqueda_nombre")
with orden_col:
    orden = st.selectbox("Ordenar por", ["Más reciente", "Precio más bajo", "Precio más alto"]) 

# --- Reset de página ---
if st.session_state.get("ultima_busqueda", "") != texto_busqueda:
    st.session_state["pagina_actual"] = 0
    st.session_state["ultima_busqueda"] = texto_busqueda
    pagina = 0

# --- Filtrado de productos ---
productos_filtrados = [p for p in todos_productos if texto_busqueda.lower() in p.get("nombre_producto", "").lower()] if texto_busqueda.strip() else todos_productos

# --- Ordenamiento ---
campo_orden = "id"
asc = False
if orden == "Precio más bajo":
    campo_orden = "precio_facebook"
    asc = True
elif orden == "Precio más alto":
    campo_orden = "precio_facebook"
    asc = False

productos_filtrados.sort(key=lambda x: x.get(campo_orden, 0), reverse=not asc)

# --- Paginación ---
productos = productos_filtrados[pagina * PRODUCTOS_POR_PAGINA : (pagina + 1) * PRODUCTOS_POR_PAGINA]

# --- Renderizar tarjetas de productos ---
def render_tarjeta_producto(prod):
    img_url = prod.get('imagen_principal_url', 'https://cdn-icons-png.flaticon.com/512/1828/1828884.png')
    nombre = prod.get('nombre_producto', 'Sin nombre')
    precio = prod.get('precio_facebook', 'N/A')

    html = f"""
        <div class='product-card-pro'>
            <img src="{img_url}" alt="Imagen de {nombre}" style='width: 170px; height: 170px; object-fit: cover; border-radius:10px; margin-bottom: 14px; border: 1px solid #f0f0f0;' />
            <div class='product-title'>{nombre}</div>
            <div style='display: flex; justify-content: center; margin-bottom: 16px;'>
                <div style='background: #eef9f0; border-radius: 14px; padding: 10px 28px; display: flex; align-items: center; gap: 8px; border: 2px solid #11bc62;'>
                    <span style='font-size: 1.3rem; color: #13ba23;'>💸</span>
                    <span style='font-weight:700; color: #13ba23;'>Precio:</span>
                    <span style='font-weight:700; color: #1545a7;'>${precio}</span>
                </div>
            </div>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    if st.button("👁️‍🗨️ Ver detalles", key=f"detalle_{prod['doc_id']}"):
        st.session_state["producto_actual"] = prod["doc_id"]
        st.query_params = {"producto_id": [prod["doc_id"]]}
        st.switch_page("pages/ver_producto.py")

# --- Renderizar catálogo ---
if productos:
    n_cols = 4
    for i in range(0, len(productos), n_cols):
        cols = st.columns(n_cols, gap="large")
        for j, prod in enumerate(productos[i:i + n_cols]):
            with cols[j]:
                render_tarjeta_producto(prod)
else:
    st.warning("No se encontraron productos con la búsqueda ingresada.")

# --- Paginación: Anterior/Siguiente ---
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("⬅️ Anterior", disabled=pagina == 0):
        st.session_state["pagina_actual"] -= 1
        st.rerun()
with col3:
    if len(productos) == PRODUCTOS_POR_PAGINA and (pagina + 1) * PRODUCTOS_POR_PAGINA < len(productos_filtrados):
        if st.button("Siguiente ➡️"):
            st.session_state["pagina_actual"] += 1
            st.rerun()
with col2:
    total_paginas = max(1, (len(productos_filtrados) + PRODUCTOS_POR_PAGINA - 1) // PRODUCTOS_POR_PAGINA)
    st.markdown(f"<center><b>Página {pagina + 1} de {total_paginas}</b></center>", unsafe_allow_html=True)

# --- Footer ---
st.markdown("""
<hr style="border-top:1.7px solid #e5e9f2;">
<div style="text-align:center;color:#8a8a8a;font-size:0.96rem;">
    MonteLameda SPA &copy; 2025 | Solo uso interno<br>
    Desarrollado por Wilmer M. 🧑‍💻
</div>
""", unsafe_allow_html=True)
