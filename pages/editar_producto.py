import streamlit as st
import firebase_config
from login_app import login, esta_autenticado, obtener_rol
import math
import ml_api  # integración MercadoLibre

# =================== UTILIDAD ======================
def to_float(val):
    try:
        return float(str(val).replace(",", ".")) if val not in [None, ""] else 0.0
    except Exception:
        return 0.0

def limpiar_valor(valor):
    if valor is None: return None
    if isinstance(valor, float) and math.isnan(valor): return None
    if isinstance(valor, list) and not valor: return None
    v = str(valor).strip().lower()
    return None if v in ["", "nan", "none", "null", "sin info", "n/a"] else str(valor).strip()

def filtrar_campos(diccionario):
    return {k: v for k, v in diccionario.items() if k and v not in [None, ""]}

# =================== AUTH & DB =====================
if not esta_autenticado():
    login()
    st.stop()

rol_usuario = obtener_rol()
if rol_usuario != "admin":
    st.error("Acceso solo para administradores.")
    st.stop()

st.set_page_config(page_title="Editar Producto", layout="wide")
db = firebase_config.db

producto_id = st.session_state.get("producto_actual")
if not producto_id:
    st.error("❌ No se proporcionó un ID de producto válido.")
    st.stop()

# =================== CARGAR PRODUCTO ===================
doc = db.collection("productos").document(producto_id).get()
if not doc.exists:
    st.error("⚠️ El producto no fue encontrado en la base de datos.")
    st.stop()
producto = doc.to_dict()

# Precargar al session_state SOLO 1 VEZ
CAMPOS_FORM = [
    "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
    "descripcion", "estado", "imagen_principal_url", "imagenes_secundarias_url", "etiquetas",
    "foto_proveedor", "precio_compra", "precio_facebook", "comision_vendedor_facebook",
    "precio_mayor_3", "precio_mercado_libre", "comision_mercado_libre", "envio_mercado_libre",
    "comision_mercado_libre_30_desc", "envio_mercado_libre_30_desc", "stock", "mostrar_catalogo",
    "id_publicacion_mercado_libre", "link_publicacion_1", "link_publicacion_2", "link_publicacion_3",
    "link_publicacion_4", "cantidad_vendida", "ultima_entrada", "ultima_salida", "ml_cat_id",
    "ml_listing_type", "ml_attrs"
]
if st.session_state.get("producto_cargado_previo") != producto_id:
    for campo in CAMPOS_FORM:
        st.session_state[campo] = producto.get(campo, "")
    st.session_state["producto_cargado_previo"] = producto_id

# =================== CSS & HEADERS =====================
st.markdown("""
<style>
body { font-family: 'Roboto', sans-serif; background-color: #f4f4f9; }
.container { max-width: 1200px; margin: auto; }
.card { background-color: #fff; padding: 20px; border-radius: 10px; box-shadow: 0px 4px 6px rgba(0,0,0,0.09); margin-bottom: 20px; }
.thumbnail { width: 80px; height: 80px; object-fit: cover; border-radius: 5px; margin-right: 10px; display: inline-block; }
.valor-positivo { color: #19c319; font-weight: bold; font-size: 1.3em; }
.valor-negativo { color: #f12b2b; font-weight: bold; font-size: 1.3em; }
.valor-iva { color: #0e7ae6; font-weight: bold; }
.resaltado { background: #e8ffe8; border-radius: 6px; padding: 2px 10px; display: inline-block; margin: 0.3em 0; }
.block-ml { background: #fffbe7; border-radius: 8px; padding: 8px 12px; margin-bottom: 10px;}
.small-label {font-size:0.97rem; color:#1860d3;font-weight:700; margin-bottom:3px;}
.radio-mlpub {margin-bottom:12px;}
</style>
""", unsafe_allow_html=True)
st.markdown("<div class='container'>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>✏️ Editar producto</h1>", unsafe_allow_html=True)
st.markdown(f"<h3 style='text-align: center; color: #205ec5;'>🆔 ID producto: {producto_id}</h3>", unsafe_allow_html=True)

# =================== BARRA PROGRESO ===================
OBLIGATORIOS = [
    "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
    "descripcion", "estado", "precio_facebook", "comision_vendedor_facebook", "precio_compra"
]
campos_llenos = sum(1 for k in OBLIGATORIOS if st.session_state.get(k))
progreso = int((campos_llenos / len(OBLIGATORIOS)) * 100)
st.progress(progreso, text=f"Formulario completado: {progreso}%")

# =================== FUNCIONES DE UI ===================
def select_categorias():
    docs_cat = db.collection("categorias").stream()
    return sorted([str(doc.to_dict()["nombre"]) for doc in docs_cat if "nombre" in doc.to_dict()])

def select_proveedores():
    docs_prov = db.collection("proveedores").stream()
    return sorted([str(doc.to_dict()["nombre"]) for doc in docs_prov if "nombre" in doc.to_dict()])

def show_thumbnails(urls):
    st.markdown(" ".join([f'<img src="{u}" class="thumbnail">' for u in urls]), unsafe_allow_html=True)

# =================== TABS ===================
tabs = st.tabs(["🧾 Identificación", "🖼️ Visuales y Descripción", "💰 Precios", "📦 Stock y Opciones", "🛒 MercadoLibre"])

# ---------- TAB 1: Identificación ----------
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Código de barra *", key="codigo_barra")
        st.text_input("Nombre del producto *", key="nombre_producto", max_chars=60)
        st.selectbox("Categoría *", options=select_categorias(), key="categoria")
    with col2:
        st.text_input("Código mínimo *", key="codigo_minimo")
        st.text_input("Marca *", key="marca")
        opciones_proveedores = select_proveedores() + ["Agregar nuevo"]
        proveedor_seleccionado = st.selectbox("Proveedor *", options=opciones_proveedores, key="proveedor")
        if proveedor_seleccionado == "Agregar nuevo":
            nuevo_prov = st.text_input("Nombre del nuevo proveedor", key="nuevo_prov")
            if nuevo_prov and nuevo_prov not in opciones_proveedores:
                if st.button("Guardar nuevo proveedor"):
                    db.collection("proveedores").add({"nombre": nuevo_prov})
                    st.success(f"Proveedor '{nuevo_prov}' agregado correctamente.")
                    st.rerun()
            proveedor_final = nuevo_prov
        else:
            proveedor_final = proveedor_seleccionado
    with col3:
        st.selectbox("Estado *", options=["Nuevo", "Usado"], key="estado")

# ---------- TAB 2: Visuales y Descripción ----------
with tabs[1]:
    st.text_area("Descripción *", key="descripcion")
    st.text_input("Imagen principal (URL)", key="imagen_principal_url")
    if st.session_state.get("imagen_principal_url", "").startswith("http"):
        st.image(st.session_state.get("imagen_principal_url"), width=200)
    st.text_input("Imágenes secundarias (URLs separadas por coma)", key="imagenes_secundarias_url")
    if st.session_state.get("imagenes_secundarias_url"):
        urls = [u.strip() for u in st.session_state["imagenes_secundarias_url"].split(",") if u.strip()]
        show_thumbnails(urls)
    st.text_input("Etiquetas", key="etiquetas")
    st.text_input("Foto de proveedor", key="foto_proveedor")

# ---------- TAB 3: Precios ----------
with tabs[2]:
    st.markdown("### Mercado Libre - Tipo de publicación", unsafe_allow_html=True)
    st.radio("Tipo publicación ML", options=["Clásico", "Premium"], key="ml_listing_type", horizontal=True)

    # --- Categoría MercadoLibre automática ---
    nombre_producto = st.session_state.get("nombre_producto", "")
    ml_cat_id, ml_cat_name = st.session_state.get("ml_cat_id", ""), st.session_state.get("ml_cat_name", "")
    if nombre_producto:
        try:
            cats = ml_api.suggest_categories(nombre_producto)
            if cats: ml_cat_id, ml_cat_name = cats[0]
        except Exception: pass
    st.session_state["ml_cat_id"], st.session_state["ml_cat_name"] = ml_cat_id, ml_cat_name

    if ml_cat_id:
        st.markdown(
            f'<div class="small-label" style="color:#205ec5;font-weight:700;margin-top:10px;">Categoría ML detectada:</div>'
            f'<b style="color:#1258ad">{ml_cat_name}</b> <span style="font-size:0.9rem;color:#999;">({ml_cat_id})</span>',
            unsafe_allow_html=True
        )

    # --- Calculo comisión ML
    precio_ml = to_float(st.session_state.get("precio_mercado_libre", 0))
    tipo_pub = st.session_state.ml_listing_type.lower()
    porcentaje, costo_fijo = ml_api.get_comision_categoria_ml(ml_cat_id, precio_ml, tipo_pub)
    comision_ml = round(precio_ml * porcentaje / 100 + costo_fijo)
    st.markdown(
        f"""<div style="background:#fffbe7;padding:7px 12px;border-radius:8px;margin-bottom:10px;margin-top:4px;font-size:1em;">
        Comisión MercadoLibre: <b>{comision_ml:,} CLP</b> ({porcentaje:.2%} del precio, costo fijo: {costo_fijo} CLP)
        </div>""",
        unsafe_allow_html=True
    )

    st.markdown("<h2 style='margin-top:1em;margin-bottom:0.2em;'>Detalles de Precios</h2>", unsafe_allow_html=True)
    col_fb, col_ml, col_ml30 = st.columns(3)

    # --- Facebook
    with col_fb:
        st.markdown("💰 <b>Facebook</b>", unsafe_allow_html=True)
        st.text_input("Precio para Facebook", key="precio_facebook")
        st.text_input("Comisión", key="comision_vendedor_facebook")
        st.text_input("Precio al por mayor de 3", key="precio_mayor_3")
        precio_fb = to_float(st.session_state.get("precio_facebook", 0))
        comision_fb = to_float(st.session_state.get("comision_vendedor_facebook", 0))
        precio_compra = to_float(st.session_state.get("precio_compra", 0))
        ganancia_fb = precio_fb - precio_compra - comision_fb
        color_fb = "valor-positivo" if ganancia_fb > 0 else "valor-negativo"
        st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_fb}'>✅ {ganancia_fb:.0f} CLP</span>", unsafe_allow_html=True)

    # --- MercadoLibre
    with col_ml:
        st.markdown("<b>Mercado Libre</b>", unsafe_allow_html=True)
        st.text_input("Precio para ML", key="precio_mercado_libre")
        st.text_input("Comisión MercadoLibre", value=f"{comision_ml:.0f}", key="comision_mercado_libre", disabled=True)
        attrs = st.session_state.get("ml_attrs", {})
        alto, ancho, largo, peso = attrs.get("HEIGHT", 0), attrs.get("WIDTH", 0), attrs.get("LENGTH", 0), attrs.get("WEIGHT", 0)
        if not (alto and ancho and largo and peso):
            st.warning("Para calcular el costo de envío, asegúrate de completar alto, ancho, largo y peso en los atributos de ML.")
            costo_envio = 0
        else:
            dimensiones_str = f"{alto}x{ancho}x{largo},{peso}"
            costo_envio, _ = ml_api.get_shipping_cost_mlc(
                item_price=precio_ml,
                dimensions=dimensiones_str,
                category_id=ml_cat_id,
                listing_type_id="gold_special" if tipo_pub in ["clásico", "clasico"] else "gold_pro",
                condition="new"
            )
        st.text_input("Costo de envío MercadoLibre", value=f"{costo_envio:.0f}", key="envio_mercado_libre", disabled=True)
        ganancia_ml_estimada = precio_ml - precio_compra - comision_ml - costo_envio
        color_ml = "valor-positivo" if ganancia_ml_estimada > 0 else "valor-negativo"
        st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_ml}'>✅ {ganancia_ml_estimada:.0f} CLP</span>", unsafe_allow_html=True)
        ganancia_bruta = precio_ml - comision_ml - costo_envio
        iva_19 = ganancia_bruta * 0.19
        ganancia_ml_neta = ganancia_bruta - iva_19 - precio_compra
        st.markdown(f"<span class='valor-iva'>🟩 Ganancia de ML descontando IVA 19%: {ganancia_ml_neta:.0f} CLP</span>", unsafe_allow_html=True)

    # --- MercadoLibre con 30% desc.
    with col_ml30:
        st.markdown("💖 <b>ML con 30% desc.</b>", unsafe_allow_html=True)
        precio_ml_30 = precio_ml * 0.7
        comision_ml_30 = round(precio_ml_30 * porcentaje / 100 + costo_fijo)
        st.text_input("Precio", value=f"{precio_ml_30:.0f}", key="precio_mercado_libre_30_desc", disabled=True)
        st.text_input("Comisión", value=f"{comision_ml_30:.0f}", key="comision_mercado_libre_30_desc", disabled=True)
        st.text_input("Envío", value="0", key="envio_mercado_libre_30_desc", disabled=True)
        ganancia_ml_desc_estimada = precio_ml_30 - precio_compra - comision_ml_30
        color_ml_desc = "valor-positivo" if ganancia_ml_desc_estimada > 0 else "valor-negativo"
        st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_ml_desc}'>✅ {ganancia_ml_desc_estimada:.0f} CLP</span>", unsafe_allow_html=True)
        ganancia_bruta_desc = precio_ml_30 - comision_ml_30
        iva_19_desc = ganancia_bruta_desc * 0.19
        ganancia_ml_desc_neta = ganancia_bruta_desc - iva_19_desc - precio_compra
        st.markdown(f"<span class='valor-iva'>🟩 Ganancia ML -30% con IVA 19%: {ganancia_ml_desc_neta:.0f} CLP</span>", unsafe_allow_html=True)

# ---------- TAB 4: Stock y otros ----------
with tabs[3]:
    for campo in ["stock", "mostrar_catalogo", "id_publicacion_mercado_libre",
                  "link_publicacion_1", "link_publicacion_2", "link_publicacion_3", "link_publicacion_4",
                  "cantidad_vendida", "ultima_entrada", "ultima_salida"]:
        st.text_input(campo.replace("_", " ").capitalize(), key=campo)

# --- (Te faltó el TAB 5 MercadoLibre atributos, agrégalo aquí si quieres) ---

# FIN DEL CÓDIGO REFACTORIZADO
