import os
import sys
import streamlit as st
import pandas as pd
from io import BytesIO

sys.path.append(os.path.join(os.path.dirname(__file__), "modulos"))
from login_app import login, esta_autenticado, obtener_rol
import firebase_config

# ─── Autenticación ───────────────────────────────────────────────────────────
if not esta_autenticado():
    login()
    st.stop()
rol_usuario = obtener_rol()  # "admin" o "vendedor"

st.set_page_config(page_title="MonteLameda System", layout="wide")

# ─── CSS Global ──────────────────────────────────────────────────────────────
st.markdown("""
    <style>
    /* botones primarios */
    div.stButton > button {
        background: linear-gradient(90deg,#2062d8 80%,#1545a7 100%)!important;
        color:#fff!important;
        border:none!important;
        border-radius:10px!important;
        padding:14px 0!important;
        width:100%!important;
        font-size:1.09rem!important;
        font-weight:700!important;
        cursor:pointer!important;
        box-shadow:0 2px 8px rgba(32,98,216,.10)!important;
        letter-spacing:.04em!important;
        outline:none!important;
        margin-top:8px!important;
    }
    div.stButton > button:hover {
        background:linear-gradient(90deg,#1545a7 80%,#2062d8 100%)!important;
        box-shadow:0 2px 16px #185cc9bb!important;
        transform:scale(1.04)!important;
    }
    .seleccion-botones button{
        width:100%!important;min-width:220px!important;max-width:100%!important;
        font-size:1.08rem!important;font-weight:700!important;padding:18px 0!important;
    }
    </style>
""", unsafe_allow_html=True)

# ─── Carga productos desde Firestore ─────────────────────────────────────────
from firebase_admin import firestore

db = firestore.client()
productos = []
try:
    docs = db.collection("productos").stream()
    for doc in docs:
        data = doc.to_dict()
        data["doc_id"] = doc.id
        productos.append(data)
except Exception as e:
    st.error(f"Error cargando productos de Firestore: {e}")

PRODUCTOS_POR_PAGINA = 12  # Puedes ajustar este número
pagina = st.session_state.get("pagina_actual", 0)
productos_filtrados = productos  # Aquí puedes aplicar filtros si tienes

# ─── Encabezado / Logo ───────────────────────────────────────────────────────
st.markdown("""
    <div style="display:flex;align-items:center;gap:22px;margin:8px 0 6px 0;">
        <img src="https://res.cloudinary.com/dkl4xbslu/image/upload/v1747363106/ChatGPT_Image_15_may_2025_22_37_31-Photoroom_yw4hqn.png" style="height:60px;width:60px;border-radius:50%;box-shadow:0 2px 16px #e0e0e0;" />
        <div style="flex-direction:column;">
            <span style="font-size:2.05rem;font-weight:900;color:#205ec5;">MonteLameda <span style='color:#1545a7;font-weight:800;'>Catálogo</span></span>
            <span style="color:#5a5a5a;font-size:1.08rem;">Gestión de productos y stock interno.</span>
        </div>
    </div>
    <hr style="border-top:1.8px solid #f2f4f9;">
""", unsafe_allow_html=True)

# ─── Favicon ─────────────────────────────────────────────────────────────────
st.markdown("""
    <link rel="icon" href="https://res.cloudinary.com/dkl4xbslu/image/upload/v1747363106/ChatGPT_Image_15_may_2025_22_37_31-Photoroom_yw4hqn.png" type="image/png" sizes="32x32">
""", unsafe_allow_html=True)

# ─── Tarjeta Producto (Corregido) ────────────────────────────────────────────
def render_tarjeta_producto(prod):
    img_url = prod.get('imagen_principal_url',
                       'https://cdn-icons-png.flaticon.com/512/1828/1828884.png')
    nombre  = prod.get('nombre_producto', 'Sin nombre')
    precio  = prod.get('precio_facebook', 'N/A')
    doc_id  = prod['doc_id']

    # Inicializa la lista de seleccionados si no existe
    if "productos_seleccionados" not in st.session_state:
        st.session_state["productos_seleccionados"] = []

    # checkbox selección
    seleccionado = st.checkbox("Seleccionar", key=f"select_{doc_id}",
                               value=doc_id in st.session_state["productos_seleccionados"])
    if seleccionado and doc_id not in st.session_state["productos_seleccionados"]:
        st.session_state["productos_seleccionados"].append(doc_id)
    elif not seleccionado and doc_id in st.session_state["productos_seleccionados"]:
        st.session_state["productos_seleccionados"].remove(doc_id)

    # tarjeta visual
    st.markdown(f"""
        <div class='product-card-pro'>
            <img src="{img_url}" style='width:170px;height:170px;object-fit:cover;
                 border-radius:10px;margin-bottom:14px;border:1px solid #f0f0f0;'/>
            <div class='product-title'>{nombre}</div>
            <div style='display:flex;justify-content:center;margin-bottom:16px;'>
                <div style='background:#eef9f0;border-radius:14px;padding:10px 28px;
                            display:flex;align-items:center;gap:8px;border:2px solid #11bc62;'>
                    <span style='font-size:1.3rem;color:#13ba23;'>💸</span>
                    <span style='font-weight:700;color:#13ba23;'>Precio:</span>
                    <span style='font-weight:700;color:#1545a7;'>${precio}</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # botones acción
    col_det, col_ml = st.columns(2, gap="small")
    with col_det:
        if st.button("👁️‍🗨️ Ver detalles", key=f"detalle_{doc_id}"):
            st.session_state["producto_actual"] = doc_id
            st.switch_page("ver_producto")

    with col_ml:
        if st.button("🛒 Publicar ML", key=f"ml_{doc_id}"):
            st.query_params["id"] = doc_id
            st.switch_page("pages/2_Mercado_Libre.py")

# ─── Render cards ───────────────────────────────────────────────────────────
if productos:
    cols = st.columns(4)
    for idx, prod in enumerate(productos):
        with cols[idx % 4]:
            render_tarjeta_producto(prod)
else:
    st.warning("No hay productos para mostrar.")

# ─── Excel descarga fotos -----------------------------------------------------------------
if st.session_state.get("productos_seleccionados"):
    seleccionados = [p for p in productos
                     if p["doc_id"] in st.session_state["productos_seleccionados"]]

    def obtener_fotos(p):
        portada = p.get("imagen_principal_url", "").strip()
        secundarias = p.get("imagenes_secundarias_url", "")
        if isinstance(secundarias, list):
            secundarias_str = ", ".join([u.strip() for u in secundarias if u.strip()])
        elif isinstance(secundarias, str):
            secundarias_str = ", ".join([u.strip() for u in secundarias.split(",") if u.strip()])
        else:
            secundarias_str = ""
        fotos = [url for url in [portada] + secundarias_str.split(",") if url.strip()]
        return ", ".join(fotos)

    df = pd.DataFrame([{
        "Titulo": p.get("nombre_producto", ""),
        "Precio": p.get("precio_facebook", ""),
        "Descripcion": p.get("descripcion", ""),
        "Categoria": p.get("categoria", ""),
        "Estado": p.get("estado", ""),
        "Etiquetas de productos": p.get("etiquetas", ""),
        "Fotos": obtener_fotos(p)
    } for p in seleccionados])

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    st.download_button("Descargar Excel de seleccionados", output,
                       "productos.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ─── Paginación ─────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if pagina > 0 and st.button("⬅️ Anterior"):
        st.session_state["pagina_actual"] = pagina - 1
with col3:
    if (pagina + 1) * PRODUCTOS_POR_PAGINA < len(productos_filtrados):
        if st.button("Siguiente ➡️"):
            st.session_state["pagina_actual"] = pagina + 1
with col2:
    total_pag = max(1, (len(productos_filtrados) - 1) // PRODUCTOS_POR_PAGINA + 1)
    st.markdown(f"<div style='text-align:center;font-size:1.1rem;'>Página {pagina + 1} de {total_pag}</div>",
                unsafe_allow_html=True)

# ─── Footer ─────────────────────────────────────────────────────────────────
st.markdown("""
<hr style="border-top:1.7px solid #e5e9f2;">
<div style="text-align:center;color:#8a8a8a;font-size:0.96rem;">
    MonteLameda SPA &copy; 2025 | Solo uso interno<br>
    Desarrollado por Wilmer M. 🧑‍💻
</div>
""", unsafe_allow_html=True)
