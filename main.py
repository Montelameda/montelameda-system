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

# ─── Helpers banner vendedor ────────────────────────────────────────────────
def obtener_banner_vendedor():
    doc = firebase_config.db.collection("config").document("banner_vendedor").get()
    return doc.to_dict().get("texto", "") if doc.exists else ""

def actualizar_banner_vendedor(nuevo_texto):
    firebase_config.db.collection("config").document("banner_vendedor").set({"texto": nuevo_texto})

if rol_usuario == "admin":
    with st.expander("Editar banner de vendedores (opcional)", expanded=False):
        texto_actual = obtener_banner_vendedor()
        nuevo_texto = st.text_area("Texto del banner para vendedores", value=texto_actual)
        if st.button("Actualizar banner"):
            actualizar_banner_vendedor(nuevo_texto)
            st.success("Banner actualizado.")

if rol_usuario == "vendedor":
    banner_texto = obtener_banner_vendedor()
    if banner_texto.strip():
        st.info(banner_texto)

# ─── CSS tarjetas producto ──────────────────────────────────────────────────
st.markdown("""
    <style>
    .product-card-pro{
        background:#fff;border-radius:16px;
        box-shadow:0 2px 18px rgba(60,60,60,.09),0 1.5px 6px rgba(32,98,216,.03);
        padding:20px 14px;min-height:410px;display:flex;
        flex-direction:column;align-items:center;margin-bottom:18px;
        transition:all .19s cubic-bezier(.4,2,.6,1);
    }
    .product-card-pro:hover{
        box-shadow:0 4px 28px rgba(60,60,60,.15),0 1.5px 12px rgba(32,98,216,.06);
        transform:translateY(-8px) scale(1.027);border:2.5px solid #205ec5;
    }
    .product-title{
        font-weight:700;font-size:1.18rem;margin-bottom:9px;color:#1b2537;
        text-align:center;overflow:hidden;display:-webkit-box;
        -webkit-line-clamp:2;-webkit-box-orient:vertical;
    }
    </style>
""", unsafe_allow_html=True)

# ─── Paginación & Estado selección ──────────────────────────────────────────
PRODUCTOS_POR_PAGINA = 20
if "pagina_actual" not in st.session_state:
    st.session_state["pagina_actual"] = 0
if "productos_seleccionados" not in st.session_state:
    st.session_state["productos_seleccionados"] = []

pagina = st.session_state["pagina_actual"]

# ─── Carga productos Firestore ──────────────────────────────────────────────
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
                       if texto_busqueda.lower() in p.get("nombre_producto", "").lower()] \
                       if texto_busqueda.strip() else todos_productos

campo_orden, asc = "id", False
if orden == "Precio más bajo":
    campo_orden, asc = "precio_facebook", True
elif orden == "Precio más alto":
    campo_orden, asc = "precio_facebook", False

productos_filtrados.sort(key=lambda x: x.get(campo_orden, 0), reverse=not asc)
productos = productos_filtrados[pagina * PRODUCTOS_POR_PAGINA:(pagina + 1) * PRODUCTOS_POR_PAGINA]

# ─── Botones selección masiva ───────────────────────────────────────────────
cols_sel = st.columns(3, gap="large")
with cols_sel[0]:
    if st.button("Seleccionar todos en esta página"):
        for prod in productos:
            if prod["doc_id"] not in st.session_state["productos_seleccionados"]:
                st.session_state["productos_seleccionados"].append(prod["doc_id"])
with cols_sel[1]:
    if st.button("Seleccionar todos los productos"):
        st.session_state["productos_seleccionados"] = [p["doc_id"] for p in todos_productos]
with cols_sel[2]:
    if st.button("Deseleccionar todos"):
        st.session_state["productos_seleccionados"] = []

# ─── Tarjeta de producto (ahora con botón ML) ───────────────────────────────
def render_tarjeta_producto(prod):
    img_url = prod.get('imagen_principal_url',
                       'https://cdn-icons-png.flaticon.com/512/1828/1828884.png')
    nombre  = prod.get('nombre_producto', 'Sin nombre')
    precio  = prod.get('precio_facebook', 'N/A')
    doc_id  = prod['doc_id']

    # checkbox de selección
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

    # botones de acción (detalles + publicar ML)
    col_det, col_ml = st.columns(2, gap="small")
    with col_det:
        if st.button("👁️‍🗨️ Ver detalles", key=f"detalle_{doc_id}"):
            st.session_state["producto_actual"] = doc_id
            st.switch_page("ver_producto")
    with col_ml:
    if st.button("🛒 Publicar ML", key=f"ml_{doc_id}"):
        st.experimental_set_query_params(id=doc_id)
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
if st.session_state["productos_seleccionados"]:
    seleccionados = [p for p in todos_productos
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
        st.session_state["pagina_actual"] -= 1
with col3:
    if (pagina + 1) * PRODUCTOS_POR_PAGINA < len(productos_filtrados):
        if st.button("Siguiente ➡️"):
            st.session_state["pagina_actual"] += 1
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
