import streamlit as st
import firebase_config
from login_app import login, esta_autenticado, obtener_rol
import datetime
import math

# --- Autenticación ---
if not esta_autenticado():
    login()
    st.stop()

rol_usuario = obtener_rol()
if rol_usuario != "admin":
    st.error("Acceso solo para administradores.")
    st.stop()

st.set_page_config(page_title="Agregar Producto", layout="wide")

db = firebase_config.db

def a_str(valor):
    if valor is None:
        return ""
    return str(valor)

def limpiar_valor(valor):
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if isinstance(valor, list) and len(valor) == 0:
        return None
    v = str(valor).strip().lower()
    if v == "" or v == "nan" or v == "none" or v == "null" or v == "sin info" or v == "n/a":
        return None
    return str(valor).strip()

def filtrar_campos(diccionario):
    return {k: v for k, v in diccionario.items() if k and v not in [None, ""]}

st.markdown("""
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
""", unsafe_allow_html=True)

st.markdown("<div class='container'>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>➕ Agregar producto</h1>", unsafe_allow_html=True)

# --- Genera ID automático simple ---
if "nuevo_id" not in st.session_state:
    st.session_state.nuevo_id = f"P{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

# --- Progreso del formulario ---
obligatorios_ids = [
    "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
    "descripcion", "estado", "precio_facebook", "comision_vendedor_facebook", "precio_compra"
]

campos_llenos = sum(1 for k in obligatorios_ids if st.session_state.get(k))
progreso = int((campos_llenos / len(obligatorios_ids)) * 100)
st.progress(progreso, text=f"Formulario completado: {progreso}%")

# --- SECCIÓN TABS ---
tabs = st.tabs(["🧾 Identificación", "🖼️ Visuales y Descripción", "💰 Precios", "📦 Stock y Opciones"])

# TAB 1: Identificación
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Código de barra *", placeholder="Ej: 1234567890", key="codigo_barra")
        st.text_input("Nombre del producto *", placeholder="Ej: Camiseta deportiva", key="nombre_producto", max_chars=60)
        docs_cat = db.collection("categorias").stream()
        categorias = sorted([a_str(doc.to_dict()["nombre"]) for doc in docs_cat if "nombre" in doc.to_dict()])
        st.selectbox("Categoría *", options=categorias, key="categoria")
    with col2:
        st.text_input("Código mínimo *", placeholder="Ej: 001", key="codigo_minimo")
        st.text_input("Marca *", placeholder="Ej: Nike", key="marca")
        docs_prov = db.collection("proveedores").stream()
        proveedores = sorted([a_str(doc.to_dict()["nombre"]) for doc in docs_prov if "nombre" in doc.to_dict()])
        opciones_proveedores = proveedores + ["Agregar nuevo"]
        proveedor_seleccionado = st.selectbox("Proveedor *", options=opciones_proveedores, key="proveedor")
        if proveedor_seleccionado == "Agregar nuevo":
            nuevo_prov = st.text_input("Nombre del nuevo proveedor", key="nuevo_prov")
            if nuevo_prov and nuevo_prov not in proveedores:
                if st.button("Guardar nuevo proveedor"):
                    db.collection("proveedores").add({"nombre": nuevo_prov})
                    st.success(f"Proveedor '{nuevo_prov}' agregado correctamente.")
                    st.rerun()
            proveedor_final = nuevo_prov
        else:
            proveedor_final = proveedor_seleccionado
    with col3:
        st.selectbox("Estado *", options=["Nuevo", "Usado"], key="estado")

# TAB 2: Visuales y Descripción
with tabs[1]:
    st.text_area("Descripción *", placeholder="Detalles del producto...", key="descripcion")
    st.text_input("Imagen principal (URL)", placeholder="https://...", key="imagen_principal_url")
    if st.session_state.get("imagen_principal_url", "").startswith("http"):
        st.image(st.session_state.get("imagen_principal_url"), width=200)
    st.text_input("Imágenes secundarias (URLs separadas por coma)", placeholder="https://..., https://...", key="imagenes_secundarias_url")
    if st.session_state.get("imagenes_secundarias_url"):
        urls = [url.strip() for url in st.session_state.get("imagenes_secundarias_url").split(",") if url.strip() != ""]
        st.markdown(" ".join([f'<img src="{u}" class="thumbnail">' for u in urls]), unsafe_allow_html=True)
    st.text_input("Etiquetas", placeholder="Palabras clave separadas por coma", key="etiquetas")
    st.text_input("Foto de proveedor", placeholder="URL de la foto", key="foto_proveedor")

# TAB 3: PRECIOS
with tabs[2]:
    st.text_input("Precio compra *", placeholder="Costo del producto", key="precio_compra")
    st.markdown("<h2 style='margin-top:1em;margin-bottom:0.2em;'>Detalles de Precios</h2>", unsafe_allow_html=True)

    col_fb, col_ml, col_ml30 = st.columns(3)
    # --- Facebook ---
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
            st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_fb}'>✅ {ganancia_fb:.0f} CLP</span>", unsafe_allow_html=True)
        except:
            st.markdown("Ganancia estimada:<br><span class='valor-negativo'>-</span>", unsafe_allow_html=True)
            ganancia_fb = None

    # --- Mercado Libre ---
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
            st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_ml}'>✅ {ganancia_ml_estimada:.0f} CLP</span>", unsafe_allow_html=True)
            ganancia_bruta = precio_ml - comision_ml - envio_ml
            iva_19 = ganancia_bruta * 0.19
            ganancia_ml_neta = ganancia_bruta - iva_19 - precio_compra
            st.markdown(f"<span class='valor-iva'>🟩 Ganancia de ML descontando IVA 19%: {ganancia_ml_neta:.0f} CLP</span>", unsafe_allow_html=True)
        except:
            st.markdown("Ganancia estimada:<br><span class='valor-negativo'>-</span>", unsafe_allow_html=True)
            ganancia_ml_estimada = None
            ganancia_ml_neta = None

    # --- ML con 30% desc. ---
    with col_ml30:
        st.markdown("📉 <b>ML con 30% desc.</b>", unsafe_allow_html=True)
        try:
            precio_ml = float(st.session_state.get("precio_mercado_libre", "0"))
            precio_ml_desc = precio_ml - (precio_ml * 0.3)
            st.text_input("Precio", value=f"{precio_ml_desc:.0f}", key="precio_mercado_libre_30_desc", disabled=True)
        except:
            st.text_input("Precio", value="", key="precio_mercado_libre_30_desc", disabled=True)
        st.text_input("Comisión", placeholder="Comisión", key="comision_mercado_libre_30_desc")
        st.text_input("Envío", placeholder="Envío", key="envio_mercado_libre_30_desc")
        try:
            precio_ml_desc = float(st.session_state.get("precio_mercado_libre_30_desc", "0"))
            comision_ml_desc = float(st.session_state.get("comision_mercado_libre_30_desc", "0"))
            envio_ml_desc = float(st.session_state.get("envio_mercado_libre_30_desc", "0"))
            precio_compra = float(st.session_state.get("precio_compra", "0"))
            ganancia_ml_desc_estimada = precio_ml_desc - precio_compra - comision_ml_desc - envio_ml_desc
            color_ml_desc = "valor-positivo" if ganancia_ml_desc_estimada > 0 else "valor-negativo"
            st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_ml_desc}'>✅ {ganancia_ml_desc_estimada:.0f} CLP</span>", unsafe_allow_html=True)
            ganancia_bruta_desc = precio_ml_desc - comision_ml_desc - envio_ml_desc
            iva_19_desc = ganancia_bruta_desc * 0.19
            ganancia_ml_desc_neta = ganancia_bruta_desc - iva_19_desc - precio_compra
            st.markdown(f"<span class='valor-iva'>🟩 Ganancia ML -30% con IVA 19%: {ganancia_ml_desc_neta:.0f} CLP</span>", unsafe_allow_html=True)
        except:
            st.markdown("Ganancia estimada:<br><span class='valor-negativo'>-</span>", unsafe_allow_html=True)
            ganancia_ml_desc_estimada = None
            ganancia_ml_desc_neta = None

# TAB 4: Stock y otros
with tabs[3]:
    st.text_input("Stock", placeholder="Cantidad en stock", key="stock")
    st.text_input("Mostrar en catálogo", placeholder="Sí/No", key="mostrar_catalogo")
    st.text_input("ID Publicación Mercado Libre", placeholder="ID de la publicación", key="id_publicacion_mercado_libre")
    st.text_input("Link publicación 1", placeholder="https://...", key="link_publicacion_1")
    st.text_input("Link publicación 2", placeholder="https://...", key="link_publicacion_2")
    st.text_input("Link publicación 3", placeholder="https://...", key="link_publicacion_3")
    st.text_input("Link publicación 4", placeholder="https://...", key="link_publicacion_4")
    st.text_input("Cantidad vendida", placeholder="Ej: 0", key="cantidad_vendida")
    st.text_input("Última entrada", placeholder="Fecha última entrada", key="ultima_entrada")
    st.text_input("Última salida", placeholder="Fecha última salida", key="ultima_salida")

# --- Diccionario FINAL de producto (38 columnas) ---
nuevo = {
    "id": st.session_state.nuevo_id,
    "codigo_barra": limpiar_valor(st.session_state.get("codigo_barra")),
    "codigo_minimo": limpiar_valor(st.session_state.get("codigo_minimo")),
    "proveedor": limpiar_valor(proveedor_final if 'proveedor_final' in locals() else st.session_state.get("proveedor")),
    "nombre_producto": limpiar_valor(st.session_state.get("nombre_producto")),
    "categoria": limpiar_valor(st.session_state.get("categoria")),
    "marca": limpiar_valor(st.session_state.get("marca")),
    "descripcion": limpiar_valor(st.session_state.get("descripcion")),
    "estado": limpiar_valor(st.session_state.get("estado")),
    "imagen_principal_url": limpiar_valor(st.session_state.get("imagen_principal_url")),
    "imagenes_secundarias_url": limpiar_valor(st.session_state.get("imagenes_secundarias_url")),
    "precio_compra": limpiar_valor(st.session_state.get("precio_compra")),
    "stock": limpiar_valor(st.session_state.get("stock")),
    "precio_facebook": limpiar_valor(st.session_state.get("precio_facebook")),
    "comision_vendedor_facebook": limpiar_valor(st.session_state.get("comision_vendedor_facebook")),
    "ganancia_facebook": str(ganancia_fb) if "ganancia_fb" in locals() and ganancia_fb is not None else "",
    "precio_mercado_libre": limpiar_valor(st.session_state.get("precio_mercado_libre")),
    "comision_mercado_libre": limpiar_valor(st.session_state.get("comision_mercado_libre")),
    "envio_mercado_libre": limpiar_valor(st.session_state.get("envio_mercado_libre")),
    "ganancia_mercado_libre": str(ganancia_ml_estimada) if "ganancia_ml_estimada" in locals() and ganancia_ml_estimada is not None else "",
    "ganancia_mercado_libre_iva": f"{ganancia_ml_neta:.0f}" if "ganancia_ml_neta" in locals() and ganancia_ml_neta is not None else "",
    "precio_mercado_libre_30_desc": f"{precio_ml_desc:.0f}" if "precio_ml_desc" in locals() else "",
    "comision_mercado_libre_30_desc": limpiar_valor(st.session_state.get("comision_mercado_libre_30_desc")),
    "envio_mercado_libre_30_desc": limpiar_valor(st.session_state.get("envio_mercado_libre_30_desc")),
    "ganancia_mercado_libre_30_desc": str(ganancia_ml_desc_estimada) if "ganancia_ml_desc_estimada" in locals() and ganancia_ml_desc_estimada is not None else "",
    "ganancia_mercado_libre_iva_30_desc": f"{ganancia_ml_desc_neta:.0f}" if "ganancia_ml_desc_neta" in locals() and ganancia_ml_desc_neta is not None else "",
    "precio_mayor_3": limpiar_valor(st.session_state.get("precio_mayor_3")),
    "mostrar_catalogo": limpiar_valor(st.session_state.get("mostrar_catalogo")),
    "id_publicacion_mercado_libre": limpiar_valor(st.session_state.get("id_publicacion_mercado_libre")),
    "link_publicacion_1": limpiar_valor(st.session_state.get("link_publicacion_1")),
    "link_publicacion_2": limpiar_valor(st.session_state.get("link_publicacion_2")),
    "link_publicacion_3": limpiar_valor(st.session_state.get("link_publicacion_3")),
    "link_publicacion_4": limpiar_valor(st.session_state.get("link_publicacion_4")),
    "etiquetas": limpiar_valor(st.session_state.get("etiquetas")),
    "foto_proveedor": limpiar_valor(st.session_state.get("foto_proveedor")),
    "cantidad_vendida": limpiar_valor(st.session_state.get("cantidad_vendida")),
    "ultima_entrada": limpiar_valor(st.session_state.get("ultima_entrada")),
    "ultima_salida": limpiar_valor(st.session_state.get("ultima_salida")),
}

# --- BOTÓN GUARDAR ---
if st.button("💾 Agregar Producto"):
    try:
        nuevo_limpio = filtrar_campos(nuevo)
        if not nuevo_limpio:
            st.error("❌ No hay datos para guardar.")
        else:
            db.collection("productos").document(nuevo["id"]).set(nuevo_limpio)
            st.success(f"✅ Producto {nuevo['id']} agregado correctamente.")
            st.balloons()
            # Solo regenera el ID y recarga la página, NO limpia manualmente el session_state (evita error de Streamlit)
            st.session_state.nuevo_id = f"P{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error guardando producto: {e}")

st.markdown("</div>", unsafe_allow_html=True)
