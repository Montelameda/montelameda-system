import streamlit as st
import sys
import os
import datetime
import math
import time

from login_app import login, esta_autenticado, obtener_rol

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "modulos"))
import firebase_config
import ml_api  # integración MercadoLibre

# === TABLA DE COMISIONES Y COSTO FIJO ML POR CATEGORÍA ===
COMISIONES_ML = {
    # cat_id : (porcentaje, costo_fijo)
    "MLC12345": (0.13, 700),   # EJEMPLO: 13%, $700
    "MLC54321": (0.17, 2500),  # EJEMPLO: 17%, $2500
    # Agrega tus categorías reales aquí
}
DEFAULT_COMISION = (0.13, 700)

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
.ml-comision-detalle { color:#205ec5; font-size:0.99em; margin-top:2px; font-weight:600; }
.ml-categoria { color:#555; font-size:1.05em; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='container'>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>✏️ Editar producto</h1>", unsafe_allow_html=True)
st.markdown(f"<h3 style='text-align: center; color: #205ec5;'>🆔 ID producto: {a_str(producto.get('id',''))}</h3>", unsafe_allow_html=True)

# --- Progreso del formulario ---
obligatorios_ids = [
    "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
    "descripcion", "estado", "precio_facebook", "comision_vendedor_facebook", "precio_compra"
]

# --- Precarga datos SOLO la primera vez por producto ---
if "form_precargado" not in st.session_state:
    for campo in [
        "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
        "descripcion", "estado", "imagen_principal_url", "imagenes_secundarias_url", "etiquetas",
        "foto_proveedor", "precio_compra", "precio_facebook", "comision_vendedor_facebook",
        "precio_mayor_3", "precio_mercado_libre", "comision_mercado_libre", "envio_mercado_libre",
        "comision_mercado_libre_30_desc", "envio_mercado_libre_30_desc", "stock", "mostrar_catalogo",
        "id_publicacion_mercado_libre", "link_publicacion_1", "link_publicacion_2", "link_publicacion_3",
        "link_publicacion_4", "cantidad_vendida", "ultima_entrada", "ultima_salida"
    ]:
        st.session_state[campo] = a_str(producto.get(campo, ""))
    st.session_state.form_precargado = True

campos_llenos = sum(1 for k in obligatorios_ids if st.session_state.get(k))
progreso = int((campos_llenos / len(obligatorios_ids)) * 100)
st.progress(progreso, text=f"Formulario completado: {progreso}%")

tabs = st.tabs(["🧾 Identificación", "🖼️ Visuales y Descripción", "💰 Precios", "📦 Stock y Opciones", "🛒 MercadoLibre"])

with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Código de barra *", key="codigo_barra")
        st.text_input("Nombre del producto *", key="nombre_producto", max_chars=60)
        docs_cat = firebase_config.db.collection("categorias").stream()
        categorias = sorted([a_str(doc.to_dict()["nombre"]) for doc in docs_cat if "nombre" in doc.to_dict()])
        st.selectbox("Categoría *", options=categorias, key="categoria")
    with col2:
        st.text_input("Código mínimo *", key="codigo_minimo")
        st.text_input("Marca *", key="marca")
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

with tabs[1]:
    st.text_area("Descripción *", key="descripcion")
    st.text_input("Imagen principal (URL)", key="imagen_principal_url")
    if st.session_state.get("imagen_principal_url", "").startswith("http"):
        st.image(st.session_state.get("imagen_principal_url"), width=200)
    st.text_input("Imágenes secundarias (URLs separadas por coma)", key="imagenes_secundarias_url")
    if st.session_state.get("imagenes_secundarias_url"):
        urls = [url.strip() for url in st.session_state.get("imagenes_secundarias_url").split(",") if url.strip() != ""]
        st.markdown(" ".join([f'<img src="{u}" class="thumbnail">' for u in urls]), unsafe_allow_html=True)
    st.text_input("Etiquetas", key="etiquetas")
    st.text_input("Foto de proveedor", key="foto_proveedor")

with tabs[2]:
    st.text_input("Precio compra *", key="precio_compra")
    st.markdown("<h2 style='margin-top:1em;margin-bottom:0.2em;'>Detalles de Precios</h2>", unsafe_allow_html=True)
    col_fb, col_ml, col_ml30 = st.columns(3)
    # --- Facebook ---
    with col_fb:
        st.markdown("💰 <b>Facebook</b>", unsafe_allow_html=True)
        st.text_input("Precio", key="precio_facebook")
        st.text_input("Comisión", key="comision_vendedor_facebook")
        st.text_input("Precio al por mayor de 3", key="precio_mayor_3")
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
        precio_ml = st.text_input("Precio para ML", key="precio_mercado_libre", value=st.session_state.get("precio_mercado_libre", ""))
        precio_ml = float(precio_ml) if precio_ml else 0
        nombre_ml = st.session_state.get("nombre_producto", "")
        cat_detected, cat_name = "", ""
        if nombre_ml:
            try:
                cats = ml_api.suggest_categories(nombre_ml)
                if cats:
                    cat_detected, cat_name = cats[0]
            except Exception:
                pass
        if not cat_detected:
            cat_detected = st.session_state.get("ml_cat_id", "")
        if cat_detected:
            st.session_state["ml_cat_id"] = cat_detected
            st.session_state["ml_cat_name"] = cat_name

        comision_porcentaje, costo_fijo = COMISIONES_ML.get(cat_detected, DEFAULT_COMISION)
        st.markdown(f"<div class='ml-categoria'><b>Categoría ML detectada:</b> {cat_detected} - {cat_name if cat_name else ''}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ml-comision-detalle'>Comisión MercadoLibre: <b>{int(comision_porcentaje*100)}%</b> + ${costo_fijo} fijo</div>", unsafe_allow_html=True)
        comision_ml = int(precio_ml * comision_porcentaje) + costo_fijo if precio_ml > 0 else 0
        st.text_input("Comisión", value=str(comision_ml), key="comision_mercado_libre", disabled=True)
        envio_ml = st.text_input("Envío", key="envio_mercado_libre", value=st.session_state.get("envio_mercado_libre", "0"))
        envio_ml = float(envio_ml) if envio_ml else 0
        precio_compra = float(st.session_state.get("precio_compra", "0"))
        try:
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
        precio_ml_desc = precio_ml - (precio_ml * 0.3)
        st.text_input("Precio", value=f"{precio_ml_desc:.0f}", key="precio_mercado_libre_30_desc", disabled=True)
        comision_ml_desc = int(precio_ml_desc * comision_porcentaje) + costo_fijo if precio_ml_desc > 0 else 0
        st.text_input("Comisión", value=str(comision_ml_desc), key="comision_mercado_libre_30_desc", disabled=True)
        envio_ml_desc = st.text_input("Envío", value=envio_ml, key="envio_mercado_libre_30_desc")
        envio_ml_desc = float(envio_ml_desc) if envio_ml_desc else 0
        try:
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

with tabs[3]:
    st.text_input("Stock", key="stock")
    st.text_input("Mostrar en catálogo", key="mostrar_catalogo")
    st.text_input("ID Publicación Mercado Libre", key="id_publicacion_mercado_libre")
    st.text_input("Link publicación 1", key="link_publicacion_1")
    st.text_input("Link publicación 2", key="link_publicacion_2")
    st.text_input("Link publicación 3", key="link_publicacion_3")
    st.text_input("Link publicación 4", key="link_publicacion_4")
    st.text_input("Cantidad vendida", key="cantidad_vendida")
    st.text_input("Última entrada", key="ultima_entrada")
    st.text_input("Última salida", key="ultima_salida")

with tabs[4]:
    st.subheader("Atributos MercadoLibre")
    nombre_ml = st.session_state.get("nombre_producto", "")
    if "ml_cat_id" not in st.session_state or st.session_state.get("ml_cat_name") is None:
        st.session_state.ml_cat_id = ""
        st.session_state.ml_cat_name = ""

    cat_detected, cat_name = "", ""
    if nombre_ml:
        try:
            cats = ml_api.suggest_categories(nombre_ml)
            if cats:
                cat_detected, cat_name = cats[0]
        except Exception:
            cat_detected, cat_name = "", ""

    if cat_detected and cat_detected != st.session_state.get("ml_cat_id", ""):
        st.session_state["ml_cat_id"] = cat_detected
        st.session_state["ml_cat_name"] = cat_name
        st.rerun()

    if "ml_cat_id" not in st.session_state or not st.session_state["ml_cat_id"]:
        st.session_state["ml_cat_id"] = cat_detected
    ml_cat_id = st.text_input("ID categoría ML", key="ml_cat_id", help="Se detecta según el título; edita si prefieres otra")

    if "last_ml_cat_id" not in st.session_state:
        st.session_state["last_ml_cat_id"] = ""
    if ml_cat_id != st.session_state["last_ml_cat_id"]:
        st.session_state["last_ml_cat_id"] = ml_cat_id
        st.session_state["ml_attrs_loaded"] = False

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

    if not req_attrs:
        st.info("No hay atributos para esta categoría, solo debes completar el resto del formulario.")
    else:
        ml_attr_vals = st.session_state.get("ml_attrs", {})
        for attr in req_attrs:
            aid = attr["id"]
            nombre = attr["name"]
            vtype = attr["value_type"]
            default_val = ml_attr_vals.get(aid,"")
            if vtype in ("boolean"):
                opt = ["Sí", "No"]
                ml_attr_vals[aid] = st.selectbox(nombre, opt, key=f"ml_{aid}_edit", index=opt.index(default_val) if default_val in opt else 0)
            elif vtype in ("list",):
                opts = [v["name"] for v in attr.get("values",[])]
                idx_def = opts.index(default_val) if default_val in opts else 0
                ml_attr_vals[aid] = st.selectbox(nombre, opts if opts else ["-"], key=f"ml_{aid}_edit", index=idx_def)
            else:
                ml_attr_vals[aid] = st.text_input(nombre, value=default_val, key=f"ml_{aid}_edit")
        st.session_state["ml_attrs"] = ml_attr_vals

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
    "comision_mercado_libre": str(comision_ml) if "comision_ml" in locals() else "",
    "envio_mercado_libre": limpiar_valor(st.session_state.get("envio_mercado_libre")),
    "ganancia_mercado_libre": str(ganancia_ml_estimada) if "ganancia_ml_estimada" in locals() and ganancia_ml_estimada is not None else "",
    "ganancia_mercado_libre_iva": f"{ganancia_ml_neta:.0f}" if "ganancia_ml_neta" in locals() and ganancia_ml_neta is not None else "",
    "precio_mercado_libre_30_desc": f"{precio_ml_desc:.0f}" if "precio_ml_desc" in locals() else "",
    "comision_mercado_libre_30_desc": str(comision_ml_desc) if "comision_ml_desc" in locals() else "",
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
}

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

st.markdown("</div>", unsafe_allow_html=True)
