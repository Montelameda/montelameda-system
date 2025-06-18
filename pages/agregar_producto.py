import streamlit as st
import firebase_config
from login_app import login, esta_autenticado, obtener_rol
import datetime
import math
import requests
import ml_api  # integración MercadoLibre

# ------------------ SEGURIDAD ------------------
if not esta_autenticado():
    login()
    st.stop()

rol_usuario = obtener_rol()
if rol_usuario != "admin":
    st.error("Acceso solo para administradores.")
    st.stop()

# ------------------ CONFIG UI ------------------
st.set_page_config(page_title="Agregar Producto", layout="wide")
db = firebase_config.db

# ------------------ HELPERS --------------------

def a_str(valor):
    return "" if valor is None else str(valor)


def limpiar_valor(valor):
    """Normaliza valores para Firestore (None en blancos, nan, etc.)"""
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if isinstance(valor, list) and len(valor) == 0:
        return None
    v = str(valor).strip().lower()
    if v in ("", "nan", "none", "null", "sin info", "n/a"):
        return None
    return str(valor).strip()


def filtrar_campos(diccionario: dict):
    """Quita claves vacías / None antes de subir a Firestore"""
    return {k: v for k, v in diccionario.items() if k and v not in [None, ""]}

# ------------------ ESTILOS --------------------
st.markdown(
    """
    <style>
    body { font-family: 'Roboto', sans-serif; background-color: #f4f4f9; }
    .container { max-width: 1200px; margin: auto; }
    .card { background-color: #fff; padding: 20px; border-radius: 10px;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.09); margin-bottom: 20px; }
    .thumbnail { width: 80px; height: 80px; object-fit: cover; border-radius: 5px; margin-right: 10px; display: inline-block; }
    .valor-positivo { color: #19c319; font-weight: bold; font-size: 1.3em; }
    .valor-negativo { color: #f12b2b; font-weight: bold; font-size: 1.3em; }
    .valor-iva { color: #0e7ae6; font-weight: bold; }
    .resaltado { background: #e8ffe8; border-radius: 6px; padding: 2px 10px; display: inline-block; margin: 0.3em 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='container'>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>➕ Agregar producto</h1>", unsafe_allow_html=True)

# --------------- ID AUTOMÁTICO -----------------
if "nuevo_id" not in st.session_state:
    st.session_state["nuevo_id"] = f"P{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

# --------------- PROGRESO ----------------------
obligatorios_ids = [
    "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
    "descripcion", "estado", "precio_facebook", "comision_vendedor_facebook", "precio_compra",
]
campos_llenos = sum(1 for k in obligatorios_ids if st.session_state.get(k))
progreso = int((campos_llenos / len(obligatorios_ids)) * 100)
st.progress(progreso, text=f"Formulario completado: {progreso}%")

# --------------- TABS --------------------------
tabs = st.tabs([
    "🧾 Identificación",
    "🖼️ Visuales y Descripción",
    "💰 Precios",
    "📦 Stock y Opciones",
    "🛒 MercadoLibre",
])

# ------------------------------------------------
# TAB 1: IDENTIFICACIÓN
# ------------------------------------------------
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    # ---- Col1 ----
    with col1:
        st.text_input("Código de barra *", placeholder="Ej: 1234567890", key="codigo_barra")
        st.text_input("Nombre del producto *", placeholder="Ej: Peluche oso 30 cm", key="nombre_producto", max_chars=60)
        # Categorías (Facebook propias)
        docs_cat = db.collection("categorias").stream()
        categorias = sorted([a_str(d.to_dict().get("nombre", "")) for d in docs_cat])
        st.selectbox("Categoría Facebook *", options=categorias, key="categoria")
    # ---- Col2 ----
    with col2:
        st.text_input("Código mínimo *", placeholder="Ej: 001", key="codigo_minimo")
        st.text_input("Marca *", placeholder="Ej: Nike", key="marca")
        docs_prov = db.collection("proveedores").stream()
        proveedores = sorted([a_str(d.to_dict().get("nombre", "")) for d in docs_prov])
        opciones_proveedores = proveedores + ["Agregar nuevo"]
        proveedor_sel = st.selectbox("Proveedor *", opciones_proveedores, key="proveedor")
        if proveedor_sel == "Agregar nuevo":
            nuevo_prov = st.text_input("Nombre del nuevo proveedor", key="nuevo_prov")
            if nuevo_prov and nuevo_prov not in proveedores:
                if st.button("Guardar nuevo proveedor"):
                    db.collection("proveedores").add({"nombre": nuevo_prov})
                    st.success(f"Proveedor '{nuevo_prov}' agregado correctamente.")
                    st.rerun()
            proveedor_final = nuevo_prov
        else:
            proveedor_final = proveedor_sel
    # ---- Col3 ----
    with col3:
        st.selectbox("Estado *", options=["Nuevo", "Usado"], key="estado")

# ------------------------------------------------
# TAB 2: VISUALES / DESCRIPCIÓN
# ------------------------------------------------
with tabs[1]:
    st.text_area("Descripción *", placeholder="Detalles del producto…", key="descripcion")
    st.text_input("Imagen principal (URL)", placeholder="https://…", key="imagen_principal_url")
    if st.session_state.get("imagen_principal_url", "").startswith("http"):
        st.image(st.session_state["imagen_principal_url"], width=200)
    st.text_input(
        "Imágenes secundarias (URLs separadas por coma)",
        placeholder="https://…, https://…",
        key="imagenes_secundarias_url",
    )
    if st.session_state.get("imagenes_secundarias_url"):
        urls = [u.strip() for u in st.session_state["imagenes_secundarias_url"].split(",") if u.strip()]
        thumbs = " ".join([f'<img src="{u}" class="thumbnail">' for u in urls])
        st.markdown(thumbs, unsafe_allow_html=True)
    st.text_input("Etiquetas", placeholder="Palabras clave…", key="etiquetas")
    st.text_input("Foto de proveedor", placeholder="URL de la foto", key="foto_proveedor")

# ------------------------------------------------
# TAB 3: PRECIOS
# ------------------------------------------------
with tabs[2]:
    st.text_input("Precio compra *", placeholder="Costo del producto", key="precio_compra")
    st.markdown("<h2 style='margin-top:1em;margin-bottom:0.2em;'>Detalles de Precios</h2>", unsafe_allow_html=True)

    col_fb, col_ml, col_ml30 = st.columns(3)

    # ------- Facebook -------
    with col_fb:
        st.markdown("💰 <b>Facebook</b>", unsafe_allow_html=True)
        st.text_input("Precio", placeholder="Precio para Facebook", key="precio_facebook")
        st.text_input("Comisión", placeholder="Comisión", key="comision_vendedor_facebook")
        st.text_input("Precio al por mayor de 3", placeholder="Precio al por mayor", key="precio_mayor_3")
        try:
            precio_fb = float(st.session_state.get("precio_facebook", "0"))
            comision_fb = float(st.session_state.get("comision_vendedor_facebook", "0"))
            precio_compra = float(st.session_state.get("precio_compra", "0"))
            ganancia_fb = precio_fb - precio_compra - comision_fb
            color_fb = "valor-positivo" if ganancia_fb > 0 else "valor-negativo"
            st.markdown(
                f"Ganancia estimada:<br><span class='resaltado {color_fb}'>✅ {ganancia_fb:.0f} CLP</span>",
                unsafe_allow_html=True,
            )
        except Exception:
            ganancia_fb = None
            st.markdown("Ganancia estimada:<br><span class='valor-negativo'>-</span>", unsafe_allow_html=True)

    # ------- Mercado Libre -------
    with col_ml:
        st.markdown("🛒 <b>Mercado Libre</b>", unsafe_allow_html=True)
        st.text_input("Precio", placeholder="Precio para ML", key="precio_mercado_libre")
        st.text_input("Comisión", placeholder="Comisión", key="comision_mercado_libre")
        st.text_input("Envío", placeholder="Costo de envío", key="envio_mercado_libre")
        try:
            precio_ml = float(st.session_state.get("precio_mercado_libre", "0"))
            comision_ml = float(st.session_state.get("comision_mercado_libre", "0"))
            envio_ml = float(st.session_state.get("envio_mercado_libre", "0"))
            precio_compra = float(st.session_state.get("precio_compra", "0"))
            ganancia_ml_estimada = precio_ml - precio_compra - comision_ml - envio_ml
            color_ml = "valor-positivo" if ganancia_ml_estimada > 0 else "valor-negativo"
            st.markdown(
                f"Ganancia estimada:<br><span class='resaltado {color_ml}'>✅ {ganancia_ml_estimada:.0f} CLP</span>",
                unsafe_allow_html=True,
            )
            ganancia_bruta = precio_ml - comision_ml - envio_ml
            iva_19 = ganancia_bruta * 0.19
            ganancia_ml_neta = ganancia_bruta - iva_19 - precio_compra
            st.markdown(
                f"<span class='valor-iva'>🟩 Ganancia de ML descontando IVA 19%: {ganancia_ml_neta:.0f} CLP</span>",
                unsafe_allow_html=True,
            )
        except Exception:
            ganancia_ml_estimada = None
            ganancia_ml_neta = None
            st.markdown("Ganancia estimada:<br><span class='valor-negativo'>-</span>", unsafe_allow_html=True)

    # ------- ML con 30 % desc. -------
    with col_ml30:
        st.markdown("📉 <b>ML con 30% desc.</b>", unsafe_allow_html=True)
        try:
            precio_ml_base = float(st.session_state.get("precio_mercado_libre", "0"))
            precio_ml_desc = precio_ml_base * 0.7
            st.text_input("Precio", value=f"{precio_ml_desc:.0f}", key="precio_mercado_libre_30_desc", disabled=True)
        except Exception:
            precio_ml_desc = 0
            st.text_input("Precio", value="", key="precio_mercado_libre_30_desc", disabled=True)
        st.text_input("Comisión", placeholder="Comisión", key="comision_mercado_libre_30_desc")
        st.text_input("Envío", placeholder="Envío", key="envio_mercado_libre_30_desc")
        try:
            precio_descr = float(st.session_state.get("precio_mercado_libre_30_desc", "0"))
            comision_descr = float(st.session_state.get("comision_mercado_libre_30_desc", "0"))
            envio_descr = float(st.session_state.get("envio_mercado_libre_30_desc", "0"))
            precio_compra = float(st.session_state.get("precio_compra", "0"))
            ganancia_ml_desc_estimada = precio_descr - precio_compra - comision_descr - envio_descr
            color_descr = "valor-positivo" if ganancia_ml_desc_estimada > 0 else "valor-negativo"
            st.markdown(
                f"Ganancia estimada:<br><span class='resaltado {color_descr}'>✅ {ganancia_ml_desc_estimada:.0f} CLP</span>",
                unsafe_allow_html=True,
            )
            ganancia_bruta_desc = precio_descr - comision_descr - envio_descr
            iva19_desc = ganancia_bruta_desc * 0.19
            ganancia_ml_desc_neta = ganancia_bruta_desc - iva19_desc - precio_compra
            st.markdown(
                f"<span class='valor-iva'>🟩 Ganancia ML -30% con IVA 19%: {ganancia_ml_desc_neta:.0f} CLP</span>",
                unsafe_allow_html=True,
            )
        except Exception:
            ganancia_ml_desc_estimada = None
            ganancia_ml_desc_neta = None
            st.markdown("Ganancia estimada:<br><span class='valor-negativo'>-</span>", unsafe_allow_html=True)

# ------------------------------------------------
# TAB 4: STOCK / OTROS
# ------------------------------------------------
with tabs[3]:
    st.text_input("Stock", placeholder="Cantidad en stock", key="stock")
    st.text_input("Mostrar en catálogo", placeholder="Sí/No", key="mostrar_catalogo")
    st.text_input("ID Publicación Mercado Libre", placeholder="ID de la publicación", key="id_publicacion_mercado_libre")
    st.text_input("Link publicación 1", placeholder="https://…", key="link_publicacion_1")
    st.text_input("Link publicación 2", placeholder="https://…", key="link_publicacion_2")
    st.text_input("Link publicación 3", placeholder="https://…", key="link_publicacion_3")
    st.text_input("Link publicación 4", placeholder="https://…", key="link_publicacion_4")
    st.text_input("Cantidad vendida", placeholder="Ej: 0", key="cantidad_vendida")
    st.text_input("Última entrada", placeholder="Fecha última entrada", key="ultima_entrada")
    st.text_input("Última salida", placeholder="Fecha última salida", key="ultima_salida")

# ------------------------------------------------
# TAB 5: MERCADOLIBRE
# ------------------------------------------------
with tabs[4]:
    st.subheader("Atributos MercadoLibre")

    # -------- 1) Detectamos categoría automáticamente --------
    titulo_prod = st.session_state.get("nombre_producto", "")
    suggested_cat_id, suggested_cat_name = (None, None)
    if titulo_prod:
        try:
            suggested_cat_id, suggested_cat_name = ml_api.predict_category(titulo_prod)
        except Exception:
            suggested_cat_id = None

    # Mostrar sugerencia
    if suggested_cat_id:
        st.info(f"Categoría sugerida ML: {suggested_cat_name} ({suggested_cat_id})")

    # -------- 2) Campo editable para ID categoría --------
    default_cat = st.session_state.get("ml_cat_id") or suggested_cat_id or ""
    ml_cat_id = st.text_input("ID categoría ML", value=default_cat, key="ml_cat_id", help="Edita si no es correcta")

    # -------- 3) Renderizamos atributos requeridos --------
    ml_attrs_vals = {}
    if ml_cat_id:
        try:
            attrs_req = ml_api.get_required_attrs(ml_cat_id)
        except requests.exceptions.RequestException as e:
            attrs_req = []
            st.warning(f"No se pudieron obtener atributos: {e}")

        if not attrs_req:
            st.warning("La categoría seleccionada no tiene atributos obligatorios o no fue posible obtenerlos.")
        for att in attrs_req:
            aid, label, vtype = att["id"], att["name"], att["value_type"]
            key_widget = f"ml_{aid}"
            if vtype == "boolean":
                ml_attrs_vals[aid] = st.selectbox(label, ["Sí", "No"], key=key_widget)
            elif vtype == "list":
                opciones = [v["name"] for v in att.get("values", [])] or ["-"]
                ml_attrs_vals[aid] = st.selectbox(label, opciones, key=key_widget)
            else:
                ml_attrs_vals[aid] = st.text_input(label, key=key_widget)
    else:
        st.warning("Escribe el título del producto para sugerir categoría ML.")

    # Guardamos en session_state para el botón final
    st.session_state["ml_attrs"] = ml_attrs_vals

# ------------------------------------------------
# GUARDAR PRODUCTO
# ------------------------------------------------

nuevo = {
    # ...
