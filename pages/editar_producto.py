import streamlit as st
import firebase_config
from login_app import login, esta_autenticado, obtener_rol
import datetime
import math
import requests
import ml_api
import time

# --- Autenticación ---
if not esta_autenticado():
    login()
    st.stop()

rol_usuario = obtener_rol()
if rol_usuario != "admin":
    st.error("Acceso solo para administradores.")
    st.stop()

st.set_page_config(page_title="Editar Producto", layout="wide")

# --- LOGICA para forzar precarga de datos si cambia de producto ---
if "producto_actual" in st.session_state:
    if st.session_state.get("producto_cargado_previo") != st.session_state["producto_actual"]:
        st.session_state.pop("form_precargado", None)
        st.session_state["producto_cargado_previo"] = st.session_state["producto_actual"]

# --- Obtener el ID del producto desde el session_state ---
producto_id = st.session_state.get("producto_actual")
if not producto_id:
    st.error("❌ No se proporcionó un ID de producto válido.")
    st.stop()

# --- Obtener datos del producto existente ---
db = firebase_config.db
doc_ref = db.collection("productos").document(producto_id)
doc = doc_ref.get()
if not doc.exists:
    st.error("⚠️ El producto no fue encontrado en la base de datos.")
    st.stop()
producto = doc.to_dict()

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

def obtener_comision_envio_ml(precio, categoria_id):
    if not precio or not categoria_id:
        return 0, 0
    url = f"https://api.mercadolibre.com/sites/MLC/listing_prices?price={precio}&category_id={categoria_id}"
    try:
        resp = requests.get(url, timeout=8).json()
        fee_info = next((f for f in resp if f['listing_type_id'] == 'gold_pro'), resp[0])
        comision = fee_info['sale_fee_amount']
        envio = fee_info.get('shipping_cost', 0)
        return comision, envio
    except Exception:
        return 0, 0

# --- Custom CSS ---
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
.promo-btn {background-color:#1e78fa;color:#fff;padding:7px 18px;font-weight:700;border:none;border-radius:9px;font-size:1.11rem;}
.promo-btn-applied {background-color:#97caff;color:#234;font-weight:700;padding:7px 18px;border:none;border-radius:9px;font-size:1.11rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='container'>", unsafe_allow_html=True)

# --- TÍTULO ---
st.markdown("<h1 style='text-align: center;'>✏️ Editar producto</h1>", unsafe_allow_html=True)
st.markdown(f"<h3 style='text-align: center; color: #205ec5;'>🆔 ID producto: {a_str(producto.get('id',''))}</h3>", unsafe_allow_html=True)

# --- Precarga datos SOLO la primera vez por producto ---
if "form_precargado" not in st.session_state:
    for key in producto:
        st.session_state[key] = a_str(producto.get(key, ""))
    st.session_state.form_precargado = True

# --- Progreso del formulario ---
obligatorios_ids = [
    "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
    "descripcion", "estado", "precio_facebook", "comision_vendedor_facebook", "precio_compra"
]
campos_llenos = sum(1 for k in obligatorios_ids if st.session_state.get(k))
progreso = int((campos_llenos / len(obligatorios_ids)) * 100)
st.progress(progreso, text=f"Formulario completado: {progreso}%")

# --- SECCIÓN TABS ---
tabs = st.tabs(["🧾 Identificación", "🖼️ Visuales y Descripción", "💰 Precios", "📦 Stock y Opciones", "🛒 MercadoLibre"])

# TAB 1: Identificación
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Código de barra *", placeholder="Ej: 1234567890", key="codigo_barra")
        st.text_input("Nombre del producto *", placeholder="Ej: Camiseta deportiva", key="nombre_producto", max_chars=60)
        docs_cat = firebase_config.db.collection("categorias").stream()
        categorias = sorted([a_str(doc.to_dict()["nombre"]) for doc in docs_cat if "nombre" in doc.to_dict()])
        st.selectbox("Categoría *", options=categorias, key="categoria")
    with col2:
        st.text_input("Código mínimo *", placeholder="Ej: 001", key="codigo_minimo")
        st.text_input("Marca *", placeholder="Ej: Nike", key="marca")
        docs_prov = firebase_config.db.collection("proveedores").stream()
        proveedores = sorted([a_str(doc.to_dict()["nombre"]) for doc in docs_prov if "nombre" in doc.to_dict()])
        opciones_proveedores = proveedores + ["Agregar nuevo"]
        proveedor_seleccionado = st.selectbox("Proveedor *", options=opciones_proveedores, key="proveedor")
        if proveedor_seleccionado == "Agregar nuevo":
            nuevo_prov = st.text_input("Nombre del nuevo proveedor", key="nuevo_prov")
            if nuevo_prov and nuevo_prov not in proveedores:
                if st.button("Guardar nuevo proveedor"):
                    firebase_config.db.collection("proveedores").add({"nombre": nuevo_prov})
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

    # --- Mercado Libre (TIEMPO REAL) ---
    with col_ml:
        st.markdown("🛒 <b>Mercado Libre</b>", unsafe_allow_html=True)
        precio_ml = st.text_input("Precio para ML", value=st.session_state.get("precio_mercado_libre", ""), key="precio_mercado_libre")
        ml_cat_id = st.session_state.get("ml_cat_id", "")
        comision_ml, envio_ml = 0, 0

        if precio_ml and ml_cat_id:
            try:
                comision_ml, envio_ml = obtener_comision_envio_ml(float(precio_ml), ml_cat_id)
            except:
                comision_ml, envio_ml = 0, 0
        st.session_state["comision_mercado_libre"] = str(comision_ml)
        st.session_state["envio_mercado_libre"] = str(envio_ml)
        st.text_input("Comisión", value=str(comision_ml), key="comision_mercado_libre", disabled=True)
        st.text_input("Envío", value=str(envio_ml), key="envio_mercado_libre", disabled=True)

        try:
            precio_compra = float(st.session_state.get("precio_compra", "0"))
            ganancia_ml_estimada = float(precio_ml) - precio_compra - float(comision_ml) - float(envio_ml)
            color_ml = "valor-positivo" if ganancia_ml_estimada > 0 else "valor-negativo"
            st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_ml}'>✅ {ganancia_ml_estimada:.0f} CLP</span>", unsafe_allow_html=True)
            ganancia_bruta = float(precio_ml) - float(comision_ml) - float(envio_ml)
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
        st.text_input("Comisión", value=st.session_state.get("comision_mercado_libre", "0"), key="comision_mercado_libre_30_desc", disabled=True)
        st.text_input("Envío", value=st.session_state.get("envio_mercado_libre", "0"), key="envio_mercado_libre_30_desc", disabled=True)
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

# TAB 5: MercadoLibre (atributos, comisión y promoción -30%)
with tabs[4]:
    st.subheader("Atributos MercadoLibre")
    nombre_ml = st.session_state.get("nombre_producto", "")
    if "ml_cat_id" not in st.session_state or st.session_state.get("ml_cat_name") is None:
        st.session_state.ml_cat_id = ""
        st.session_state.ml_cat_name = ""

    # Detectar categoría ML si cambia el nombre del producto
    cat_detected, cat_name = "", ""
    if nombre_ml:
        try:
            cats = ml_api.suggest_categories(nombre_ml)
            if cats:
                cat_detected, cat_name = cats[0]
        except Exception as e:
            cat_detected, cat_name = "", ""

    # Guardar categoría detectada en session_state (solo si cambia)
    if cat_detected and cat_detected != st.session_state.get("ml_cat_id", ""):
        st.session_state["ml_cat_id"] = cat_detected
        st.session_state["ml_cat_name"] = cat_name
        st.rerun()

    # Quita el warning de Streamlit: solo key, setea antes el valor
    if "ml_cat_id" not in st.session_state or not st.session_state["ml_cat_id"]:
        st.session_state["ml_cat_id"] = cat_detected
    ml_cat_id = st.text_input("ID categoría ML", key="ml_cat_id", help="Se detecta según el título; edita si prefieres otra")

    # Si editan la categoría manual, refrescar atributos
    if "last_ml_cat_id" not in st.session_state:
        st.session_state["last_ml_cat_id"] = ""
    if ml_cat_id != st.session_state["last_ml_cat_id"]:
        st.session_state["last_ml_cat_id"] = ml_cat_id
        st.session_state["ml_attrs_loaded"] = False

    # Obtener y mostrar atributos ML (TODOS)
    req_attrs = []
    if ml_cat_id and (not st.session_state.get("ml_attrs_loaded", False)):
        try:
            req_attrs = ml_api.get_all_attrs(ml_cat_id)
            st.session_state["req_attrs"] = req_attrs
            st.session_state["ml_attrs_loaded"] = True
        except Exception as e:
            st.warning(f"No se pudieron obtener atributos: {e}")
            st.session_state["req_attrs"] = []
    else:
        req_attrs = st.session_state.get("req_attrs", [])

    # Mostrar todos los atributos aunque no sean obligatorios
    if not req_attrs:
        st.info("No hay atributos para esta categoría, solo debes completar el resto del formulario.")
    else:
        ml_attr_vals = {}
        for attr in req_attrs:
            aid = attr["id"]
            nombre = attr["name"]
            vtype = attr["value_type"]
            if vtype in ("boolean"):
                opt = ["Sí", "No"]
                ml_attr_vals[aid] = st.selectbox(nombre, opt, key=f"ml_{aid}_edit")
            elif vtype in ("list",):
                opt = [v["name"] for v in attr.get("values", [])]
                ml_attr_vals[aid] = st.selectbox(nombre, opt if opt else ["-"], key=f"ml_{aid}_edit")
            else:
                ml_attr_vals[aid] = st.text_input(nombre, key=f"ml_{aid}_edit")

        st.session_state["ml_attrs"] = ml_attr_vals

    # Botón de PROMOCIÓN -30% solo si ya tiene ID de publicación (y no está aplicado)
    id_pub = st.session_state.get("id_publicacion_mercado_libre")
    en_promo = st.session_state.get("en_promocion", False)
    if id_pub and not en_promo:
        if st.button("Aplicar promoción -30%", key="btn_promo_edit", help="Aplica precio, comisión y envío para el 30% OFF"):
            precio_ml = float(st.session_state.get("precio_mercado_libre", 0))
            precio_ml_desc = round(precio_ml * 0.7, 2)
            comision_ml = float(st.session_state.get("comision_mercado_libre", 0))
            envio_ml = float(st.session_state.get("envio_mercado_libre", 0))
            st.session_state["precio_mercado_libre_30_desc"] = precio_ml_desc
            st.session_state["comision_mercado_libre_30_desc"] = comision_ml
            st.session_state["envio_mercado_libre_30_desc"] = envio_ml
            st.session_state["en_promocion"] = True
            st.success("¡Promoción -30% aplicada con éxito!")
    elif id_pub and en_promo:
        st.button("Promoción ya aplicada", disabled=True, key="btn_promo_applied_edit")

# --- Diccionario FINAL de producto ---
nuevos = {
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
    "ml_cat_id": limpiar_valor(st.session_state.get("ml_cat_id")),
    "ml_attrs": st.session_state.get("ml_attrs"),
    "en_promocion": st.session_state.get("en_promocion", False),
}

# --- BOTÓN ACTUALIZAR ---
if st.button("💾 Actualizar Producto"):
    try:
        nuevos_limpios = filtrar_campos(nuevos)
        if not nuevos_limpios:
            st.error("❌ No hay cambios para actualizar (diccionario vacío).")
        else:
            doc_ref.update(nuevos_limpios)
            st.success(f"✅ Producto {a_str(producto.get('id',''))} actualizado correctamente.")
            st.balloons()
            time.sleep(2)
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error actualizando producto: {e}")

# --- BOTÓN ELIMINAR PRODUCTO (Solo admins) ---
if rol_usuario == "admin":
    st.markdown("---")
    if st.button("🗑️ Eliminar producto", type="secondary"):
        st.session_state.confirmar_eliminar = True

    if st.session_state.get("confirmar_eliminar", False):
        st.warning("¿Seguro que quieres eliminar este producto? Esta acción es irreversible.")
        col_confirm, col_cancel = st.columns([1,1])
        with col_confirm:
            if st.button("❌ Sí, eliminar definitivamente", key="eliminar_ahora"):
                try:
                    db.collection("productos").document(producto_id).delete()
                    st.success(f"✅ Producto {producto_id} eliminado correctamente.")
                    st.session_state.confirmar_eliminar = False
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error eliminando producto: {e}")
        with col_cancel:
            if st.button("Cancelar", key="cancelar_eliminar"):
                st.session_state.confirmar_eliminar = False

st.markdown("</div>", unsafe_allow_html=True)
