import streamlit as st
import datetime, math, requests

from login_app import login, esta_autenticado, obtener_rol
import firebase_config
import ml_api  # integración MercadoLibre

# -------------- SEGURIDAD --------------
if not esta_autenticado():
    login()
    st.stop()

if obtener_rol() != "admin":
    st.error("Acceso solo para administradores.")
    st.stop()

# -------------- CONFIG GLOBAL --------------
st.set_page_config(page_title="Agregar Producto", layout="wide")
db = firebase_config.db

# ---------- HELPERS ----------

def a_str(v):
    return "" if v is None else str(v)

def limpiar_valor(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, list) and len(v) == 0:
        return None
    txt = str(v).strip()
    if txt.lower() in ("", "nan", "none", "null", "sin info", "n/a"):
        return None
    return txt

def filtrar_campos(diccionario):
    return {k: v for k, v in diccionario.items() if k and v not in [None, ""]}

# ---------- CSS ----------
st.markdown(
    """
<style>
body {font-family:'Roboto',sans-serif;background:#f4f4f9;}
.container {max-width:1200px;margin:auto;}
.card {background:#fff;padding:20px;border-radius:10px;box-shadow:0 4px 6px rgba(0,0,0,0.09);margin-bottom:20px;}
.thumbnail {width:80px;height:80px;object-fit:cover;border-radius:5px;margin-right:10px;display:inline-block;}
.valor-positivo{color:#19c319;font-weight:bold;font-size:1.3em;}
.valor-negativo{color:#f12b2b;font-weight:bold;font-size:1.3em;}
.valor-iva{color:#0e7ae6;font-weight:bold;}
.resaltado{background:#e8ffe8;border-radius:6px;padding:2px 10px;display:inline-block;margin:0.3em 0;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='container'>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align:center;'>➕ Agregar producto</h1>", unsafe_allow_html=True)

# ---------- ID Automático ----------
if "nuevo_id" not in st.session_state:
    st.session_state.nuevo_id = f"P{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

# ---------- PROGRESO ----------
OBLIGATORIOS = [
    "codigo_barra","codigo_minimo","proveedor","nombre_producto","categoria","marca",
    "descripcion","estado","precio_facebook","comision_vendedor_facebook","precio_compra"
]
llenos = sum(1 for c in OBLIGATORIOS if st.session_state.get(c))
prog = int((llenos / len(OBLIGATORIOS)) * 100)
st.progress(prog, text=f"Formulario completado: {prog}%")

# ---------- TABS ----------
tabs = st.tabs([
    "🧾 Identificación",
    "🖼️ Visuales y Descripción",
    "💰 Precios",
    "📦 Stock y Opciones",
    "🛒 MercadoLibre",
])

# ---------- TAB 1: IDENTIFICACIÓN ----------
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Código de barra *", key="codigo_barra", placeholder="Ej: 1234567890")
        st.text_input("Nombre del producto *", key="nombre_producto", placeholder="Ej: Peluche conejo", max_chars=60)
        categorias = sorted([a_str(d.to_dict()["nombre"]) for d in db.collection("categorias").stream() if "nombre" in d.to_dict()])
        st.selectbox("Categoría Facebook *", opciones:=categorias, key="categoria")
    with col2:
        st.text_input("Código mínimo *", key="codigo_minimo", placeholder="Ej: 001")
        st.text_input("Marca *", key="marca", placeholder="Ej: Hasbro")
        proveedores = sorted([a_str(d.to_dict()["nombre"]) for d in db.collection("proveedores").stream() if "nombre" in d.to_dict()])
        prov_sel = st.selectbox("Proveedor *", opciones:=proveedores + ["Agregar nuevo"], key="proveedor")
        if prov_sel == "Agregar nuevo":
            nuevo_prov = st.text_input("Nombre del nuevo proveedor", key="nuevo_prov")
            if nuevo_prov and nuevo_prov not in proveedores and st.button("Guardar nuevo proveedor"):
                db.collection("proveedores").add({"nombre": nuevo_prov})
                st.success(f"Proveedor '{nuevo_prov}' agregado.")
                st.rerun()
            proveedor_final = nuevo_prov
        else:
            proveedor_final = prov_sel
    with col3:
        st.selectbox("Estado *", ["Nuevo", "Usado"], key="estado")

# ---------- TAB 2: VISUALES Y DESCRIPCIÓN ----------
with tabs[1]:
    st.text_area("Descripción *", key="descripcion", placeholder="Detalles del producto…")
    st.text_input("Imagen principal (URL)", key="imagen_principal_url", placeholder="https://...")
    if st.session_state.get("imagen_principal_url", "").startswith("http"):
        st.image(st.session_state["imagen_principal_url"], width=200)
    st.text_input("Imágenes secundarias (URLs, separadas por coma)", key="imagenes_secundarias_url", placeholder="https://... , https://...")
    if urls:=st.session_state.get("imagenes_secundarias_url"):
        thumbs = " ".join([f'<img src="{u.strip()}" class="thumbnail">' for u in urls.split(",") if u.strip()])
        st.markdown(thumbs, unsafe_allow_html=True)
    st.text_input("Etiquetas", key="etiquetas", placeholder="palabra1, palabra2")
    st.text_input("Foto proveedor", key="foto_proveedor", placeholder="URL")

# ---------- TAB 3: PRECIOS ----------
with tabs[2]:
    st.text_input("Precio compra *", key="precio_compra", placeholder="Costo CLP")
    col_fb, col_ml, col_ml30 = st.columns(3)
    with col_fb:
        st.markdown("💰 **Facebook**")
        st.text_input("Precio", key="precio_facebook")
        st.text_input("Comisión vendedor", key="comision_vendedor_facebook")
        st.text_input("Precio al por mayor x3", key="precio_mayor_3")
        try:
            precio_fb = float(st.session_state.get("precio_facebook", "0"))
            comision_fb = float(st.session_state.get("comision_vendedor_facebook", "0"))
            costo = float(st.session_state.get("precio_compra", "0"))
            ganancia_fb = precio_fb - costo - comision_fb
            color = "valor-positivo" if ganancia_fb > 0 else "valor-negativo"
            st.markdown(f"Ganancia estimada: <span class='{color}'>${ganancia_fb:,.0f}</span>", unsafe_allow_html=True)
        except ValueError:
            st.write("Ingresa números válidos para calcular ganancia.")
    # --- MercadoLibre cálculos originales siguen sin cambios ---
    with col_ml:
        st.markdown("💰 **MercadoLibre**")
        st.text_input("Precio venta", key="precio_mercado_libre")
        st.text_input("Comisión ML", key="comision_mercado_libre")
        st.text_input("Envío ML", key="envio_mercado_libre")
    with col_ml30:
        st.markdown("💰 **ML -30 %**")
        st.text_input("Precio -30 %", key="precio_mercado_libre_30_desc")
        st.text_input("Comisión", key="comision_mercado_libre_30_desc")
        st.text_input("Envío", key="envio_mercado_libre_30_desc")

# ---------- TAB 4: STOCK Y OPCIONES ----------
with tabs[3]:
    st.text_input("Stock", key="stock", placeholder="Unidades disponibles")
    st.text_input("Código interno ML", key="id_publicacion_mercado_libre", placeholder="ID de publicación")
    col_link1, col_link2 = st.columns(2)
    with col_link1:
        st.text_input("Link publicación 1", key="link_publicacion_1")
        st.text_input("Link publicación 3", key="link_publicacion_3")
    with col_link2:
        st.text_input("Link publicación 2", key="link_publicacion_2")
        st.text_input("Link publicación 4", key="link_publicacion_4")
    st.text_input("Cantidad vendida", key="cantidad_vendida")

# ---------- TAB 5: MERCADOLIBRE ----------
with tabs[4]:
    st.markdown("### Atributos MercadoLibre")
    titulo = st.session_state.get("nombre_producto", "").strip()
    ml_cat_id, ml_cat_name = None, None
    if titulo:
        sugerencias = ml_api.suggest_categories(titulo)
        if sugerencias:
            opciones = [n for _, n in sugerencias]
            sel = st.selectbox("Categoría sugerida", opciones, index=0)
            ml_cat_id, ml_cat_name = sugerencias[opciones.index(sel)]
        else:
            st.warning("No se encontraron categorías ML para este título. Ingresa el ID manualmente.")
    ml_cat_id = st.text_input("ID categoría ML", value=ml_cat_id or st.session_state.get("ml_cat_id", ""))
    st.session_state["ml_cat_id"] = ml_cat_id

    ml_attrs = st.session_state.get("ml_attrs", {})
    if ml_cat_id:
        try:
            for att in ml_api.get_required_attrs(ml_cat_id):
                aid, label = att["id"], att["name"]
                vtype = att["value_type"]
                if vtype in ("list", "boolean"):
                    opts = [v["name"] for v in att.get("values", [])] or ["Sí", "No"]
                    ml_attrs[aid] = st.selectbox(label, opts, key=f"ml_{aid}")
                else:
                    ml_attrs[aid] = st.text_input(label, key=f"ml_{aid}")
            st.session_state["ml_attrs"] = ml_attrs
        except requests.exceptions.RequestException as e:
            st.error(f"No se pudieron obtener atributos: {e}")

# ---------- BOTÓN GUARDAR ----------
if st.button("💾 Agregar Producto"):
    nuevo = {
        "id": st.session_state.nuevo_id,
        "codigo_barra": limpiar_valor(st.session_state.get("codigo_barra")),
        "codigo_minimo": limpiar_valor(st.session_state.get("codigo_minimo")),
        "proveedor": limpiar_valor(proveedor_final),
        "nombre_producto": limpiar_valor(st.session_state.get("nombre_producto")),
        "categoria": limpiar_valor(st.session_state.get("categoria")),
        "marca": limpiar_valor(st.session_state.get("marca")),
        "descripcion": limpiar_valor(st.session_state.get("descripcion")),
        "estado": limpiar_valor(st.session_state.get("estado")),
        "imagen_principal_url": limpiar_valor(st.session_state.get("imagen_principal_url")),
        "imagenes_secundarias_url": limpiar_valor(st.session_state.get("imagenes_secundarias_url")),
        "etiquetas": limpiar_valor(st.session_state.get("etiquetas")),
        "foto_proveedor": limpiar_valor(st.session_state.get("foto_proveedor")),
        "precio_compra": limpiar_valor(st.session_state.get("precio_compra")),
        "precio_facebook": limpiar_valor(st.session_state.get("precio_facebook")),
        "comision_vendedor_facebook": limpiar_valor(st.session_state.get("comision_vendedor_facebook")),
        "precio_mayor_3": limpiar_valor(st.session_state.get("precio_mayor_3")),
        "precio_mercado_libre": limpiar_valor(st.session_state.get("precio_mercado_libre")),
        "comision_mercado_libre": limpiar_valor(st.session_state.get("comision_mercado_libre")),
        "envio_mercado_libre": limpiar_valor(st.session_state.get("envio_mercado_libre")),
        "precio_mercado_libre_30_desc": limpiar_valor(st.session_state.get("precio_mercado_libre_30_desc")),
        "comision_mercado_libre_30_desc": limpiar_valor(st.session_state.get("comision_mercado_libre_30_desc")),
        "envio_mercado_libre_30_desc": limpiar_valor(st.session_state.get("envio_mercado_libre_30_desc")),
        "stock": limpiar_valor(st.session_state.get("stock")),
        "id_publicacion_mercado_libre": limpiar_valor(st.session_state.get("id_publicacion_mercado_libre")),
        "link_publicacion_1": limpiar_valor(st.session_state.get("link_publicacion_1")),
        "link_publicacion_2": limpiar_valor(st.session_state.get("link_publicacion_2")),
        "link_publicacion_3": limpiar_valor(st.session_state.get("link_publicacion_3")),
        "link_publicacion_4": limpiar_valor(st.session_state.get("link_publicacion_4")),
        "cantidad_vendida": limpiar_valor(st.session_state.get("cantidad_vendida")),
        "ml_cat_id": limpiar_valor(st.session_state.get("ml_cat_id")),
        "ml_attrs": st.session_state.get("ml_attrs"),
    }
    try:
        nuevo_limpio = filtrar_campos(nuevo)
        if not nuevo_limpio:
            st.error("❌ No hay datos para guardar.")
        else:
            db.collection("productos").document(nuevo["id"]).set(nuevo_limpio)
            st.success(f"✅ Producto {nuevo['id']} agregado correctamente.")
            st.balloons()
            st.session_state.clear()
            st.rerun()
    except Exception as err:
        st.error(f"❌ Error guardando producto: {err}")

st.markdown("</div>", unsafe_allow_html=True)
