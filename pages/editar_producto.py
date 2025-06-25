import streamlit as st
import firebase_config
from login_app import login, esta_autenticado, obtener_rol
import datetime
import math
import time
import ml_api  # integración MercadoLibre

# --- Autenticación ---
if not esta_autenticado():
    login()
    st.stop()

rol_usuario = obtener_rol()
if rol_usuario != "admin":
    st.error("Acceso solo para administradores.")
    st.stop()

st.set_page_config(page_title="Editar Producto", layout="wide")
db = firebase_config.db

# --- Obtener el ID del producto desde el session_state ---
producto_id = st.session_state.get("producto_actual")
if not producto_id:
    st.error("❌ No se proporcionó un ID de producto válido.")
    st.stop()

# --- Obtener datos del producto existente ---
doc_ref = db.collection("productos").document(producto_id)
doc = doc_ref.get()
if not doc.exists:
    st.error("⚠️ El producto no fue encontrado en la base de datos.")
    st.stop()
producto = doc.to_dict()

# === FUNCIONES UTILIDAD ===
def to_float(val):
    if val is None or str(val).strip() == "":
        return 0.0
    try:
        return float(str(val).replace(",", "."))
    except Exception:
        return 0.0

def limpiar_valor(valor):
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if isinstance(valor, list) and len(valor) == 0:
        return None
    v = str(valor).strip().lower()
    if v in ["", "nan", "none", "null", "sin info", "n/a"]:
        return None
    return str(valor).strip()

def filtrar_campos(diccionario):
    return {k: v for k, v in diccionario.items() if k and v not in [None, ""]}

# --- Precarga SOLO la primera vez ---
if "form_precargado" not in st.session_state or st.session_state.get("form_precargado_id") != producto_id:
    for campo in [
        "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
        "descripcion", "estado", "imagen_principal_url", "imagenes_secundarias_url", "etiquetas",
        "foto_proveedor", "precio_compra", "precio_facebook", "comision_vendedor_facebook",
        "precio_mayor_3", "precio_mercado_libre", "comision_mercado_libre", "envio_mercado_libre",
        "comision_mercado_libre_30_desc", "envio_mercado_libre_30_desc", "stock", "mostrar_catalogo",
        "id_publicacion_mercado_libre", "link_publicacion_1", "link_publicacion_2", "link_publicacion_3",
        "link_publicacion_4", "cantidad_vendida", "ultima_entrada", "ultima_salida",
        "ml_cat_id", "ml_listing_type"
    ]:
        st.session_state[campo] = str(producto.get(campo, "") if producto.get(campo) is not None else "")
    st.session_state["ml_attrs"] = producto.get("ml_attrs", {})
    st.session_state.form_precargado = True
    st.session_state.form_precargado_id = producto_id

# --- PROGRESO ---
obligatorios_ids = [
    "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
    "descripcion", "estado", "precio_facebook", "comision_vendedor_facebook", "precio_compra"
]
campos_llenos = sum(1 for k in obligatorios_ids if st.session_state.get(k))
progreso = int((campos_llenos / len(obligatorios_ids)) * 100)
st.progress(progreso, text=f"Formulario completado: {progreso}%")

# --- CSS (idéntico a agregar) ---
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
.block-ml { background: #fffbe7; border-radius: 8px; padding: 8px 12px; margin-bottom: 10px;}
.small-label {font-size:0.97rem; color:#1860d3;font-weight:700; margin-bottom:3px;}
.radio-mlpub {margin-bottom:12px;}
</style>
""", unsafe_allow_html=True)
st.markdown("<div class='container'>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>✏️ Editar producto</h1>", unsafe_allow_html=True)

# --- TABS ---
tabs = st.tabs(["🧾 Identificación", "🖼️ Visuales y Descripción", "💰 Precios", "📦 Stock y Opciones", "🛒 MercadoLibre"])

# TAB 1: Identificación
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Código de barra *", key="codigo_barra")
        st.text_input("Nombre del producto *", key="nombre_producto", max_chars=60)
        docs_cat = db.collection("categorias").stream()
        categorias = sorted([str(doc.to_dict()["nombre"]) for doc in docs_cat if "nombre" in doc.to_dict()])
        st.selectbox("Categoría *", options=categorias, key="categoria")
    with col2:
        st.text_input("Código mínimo *", key="codigo_minimo")
        st.text_input("Marca *", key="marca")
        docs_prov = db.collection("proveedores").stream()
        proveedores = sorted([str(doc.to_dict()["nombre"]) for doc in docs_prov if "nombre" in doc.to_dict()])
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

# TAB 3: PRECIOS (idéntico lógica agregar)
with tabs[2]:
    st.markdown("### Mercado Libre - Tipo de publicación", unsafe_allow_html=True)

    # --- ANTI-BOMBA para ml_listing_type ---
    opciones_ml = ["Clásico", "Premium"]
    if st.session_state.get("ml_listing_type") not in opciones_ml:
        st.session_state["ml_listing_type"] = "Clásico"

    st.radio(
        "Tipo publicación ML",
        options=opciones_ml,
        key="ml_listing_type",
        horizontal=True,
        label_visibility="visible"
    )
    # --- Detección de categoría ML ---
    nombre_producto = st.session_state.get("nombre_producto", "")
    ml_cat_id, ml_cat_name = "", ""
    if nombre_producto:
        try:
            cats = ml_api.suggest_categories(nombre_producto)
            if cats:
                ml_cat_id, ml_cat_name = cats[0]
        except Exception:
            pass
    st.session_state["ml_cat_id"] = ml_cat_id
    st.session_state["ml_cat_name"] = ml_cat_name

    # --- Mostrar categoría detectada ---
    if ml_cat_id:
        st.markdown(
            f'<div class="small-label" style="color:#205ec5;font-weight:700;margin-top:10px;">Categoría ML detectada:</div>'
            f'<b style="color:#1258ad">{ml_cat_name}</b> <span style="font-size:0.9rem;color:#999;">({ml_cat_id})</span>',
            unsafe_allow_html=True
        )

    # --- Calcular comisión ML ---
    precio_ml = to_float(st.session_state.get("precio_mercado_libre", 0))
    tipo_pub = st.session_state.ml_listing_type.lower()
    porcentaje, costo_fijo = ml_api.get_comision_categoria_ml(ml_cat_id, precio_ml, tipo_pub)
    comision_ml = round(precio_ml * porcentaje / 100 + costo_fijo)
    st.markdown(
        f"""<div style="background:#fffbe7;padding:7px 12px;border-radius:8px;margin-bottom:10px;margin-top:4px;font-size:1em;">
        Comisión MercadoLibre: <b>{comision_ml:,} CLP</b> ({porcentaje:.2f}% del precio, costo fijo: {costo_fijo} CLP)
        </div>""",
        unsafe_allow_html=True
    )

    st.markdown("<h2 style='margin-top:1em;margin-bottom:0.2em;'>Detalles de Precios</h2>", unsafe_allow_html=True)
    col_fb, col_ml, col_ml30 = st.columns(3)

    # --- Facebook (izquierda) ---
    with col_fb:
        st.markdown("💰 <b>Facebook</b>", unsafe_allow_html=True)
        st.text_input("Precio para Facebook", key="precio_facebook")
        st.text_input("Comisión", key="comision_vendedor_facebook")
        st.text_input("Precio al por mayor de 3", key="precio_mayor_3")
        try:
            precio_fb = to_float(st.session_state.get("precio_facebook", 0))
            comision_fb = to_float(st.session_state.get("comision_vendedor_facebook", 0))
            precio_compra = to_float(st.session_state.get("precio_compra", 0))
            ganancia_fb = precio_fb - precio_compra - comision_fb
            color_fb = "valor-positivo" if ganancia_fb > 0 else "valor-negativo"
            st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_fb}'>✅ {ganancia_fb:.0f} CLP</span>", unsafe_allow_html=True)
        except:
            st.markdown("Ganancia estimada:<br><span class='valor-negativo'>-</span>", unsafe_allow_html=True)
            ganancia_fb = None

    # --- MercadoLibre (centro) ---
    with col_ml:
        st.markdown("<b>Mercado Libre</b>", unsafe_allow_html=True)
        st.text_input("Precio para ML", key="precio_mercado_libre")
        st.text_input("Comisión MercadoLibre", value=f"{comision_ml:.0f}", key="comision_mercado_libre", disabled=True)

        # --- Cálculo de envío ---
        attrs = st.session_state.get("ml_attrs", {})
        alto = attrs.get("HEIGHT", 0)
        ancho = attrs.get("WIDTH", 0)
        largo = attrs.get("LENGTH", 0)
        peso = attrs.get("WEIGHT", 0)
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

        try:
            precio_compra = to_float(st.session_state.get("precio_compra", 0))
            ganancia_ml_estimada = precio_ml - precio_compra - comision_ml - costo_envio
            color_ml = "valor-positivo" if ganancia_ml_estimada > 0 else "valor-negativo"
            st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_ml}'>✅ {ganancia_ml_estimada:.0f} CLP</span>", unsafe_allow_html=True)
            ganancia_bruta = precio_ml - comision_ml - costo_envio
            iva_19 = ganancia_bruta * 0.19
            ganancia_ml_neta = ganancia_bruta - iva_19 - precio_compra
            st.markdown(f"<span class='valor-iva'>🟩 Ganancia de ML descontando IVA 19%: {ganancia_ml_neta:.0f} CLP</span>", unsafe_allow_html=True)
        except:
            st.markdown("Ganancia estimada:<br><span class='valor-negativo'>-</span>", unsafe_allow_html=True)
            ganancia_ml_estimada = None
            ganancia_ml_neta = None

    # --- MercadoLibre con 30% desc. (derecha) ---
    with col_ml30:
        st.markdown("💖 <b>ML con 30% desc.</b>", unsafe_allow_html=True)
        precio_ml_30 = precio_ml * 0.7
        porcentaje_30, costo_fijo_30 = porcentaje, costo_fijo
        comision_ml_30 = round(precio_ml_30 * porcentaje_30 / 100 + costo_fijo_30)
        st.text_input("Precio", value=f"{precio_ml_30:.0f}", key="precio_mercado_libre_30_desc", disabled=True)
        st.text_input("Comisión", value=f"{comision_ml_30:.0f}", key="comision_mercado_libre_30_desc", disabled=True)
        st.text_input("Envío", value="0", key="envio_mercado_libre_30_desc", disabled=True)
        try:
            envio_ml_30 = 0
            precio_compra = to_float(st.session_state.get("precio_compra", 0))
            ganancia_ml_desc_estimada = precio_ml_30 - precio_compra - comision_ml_30 - envio_ml_30
            color_ml_desc = "valor-positivo" if ganancia_ml_desc_estimada > 0 else "valor-negativo"
            st.markdown(f"Ganancia estimada:<br><span class='resaltado {color_ml_desc}'>✅ {ganancia_ml_desc_estimada:.0f} CLP</span>", unsafe_allow_html=True)
            ganancia_bruta_desc = precio_ml_30 - comision_ml_30 - envio_ml_30
            iva_19_desc = ganancia_bruta_desc * 0.19
            ganancia_ml_desc_neta = ganancia_bruta_desc - iva_19_desc - precio_compra
            st.markdown(f"<span class='valor-iva'>🟩 Ganancia ML -30% con IVA 19%: {ganancia_ml_desc_neta:.0f} CLP</span>", unsafe_allow_html=True)
        except:
            st.markdown("Ganancia estimada:<br><span class='valor-negativo'>-</span>", unsafe_allow_html=True)
            ganancia_ml_desc_estimada = None
            ganancia_ml_desc_neta = None

# --- TAB 4: Stock y otros
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

# TAB 5: MercadoLibre (atributos oficiales ML, igual a agregar)
with tabs[4]:
    st.subheader("Atributos MercadoLibre")
    ml_cat_id = st.session_state.get("ml_cat_id", "")
    ml_attrs = {}

    if ml_cat_id:
        attrs = ml_api.get_all_attrs(ml_cat_id)
        campos = []
        for a in attrs:
            tags = a.get("tags", {})
            if tags.get("required") or tags.get("conditional_required") or tags.get("new_required"):
                campos.append((1, a))
            elif float(a.get("relevance", 0)) >= 0.8:
                campos.append((2, a))
            else:
                campos.append((3, a))
        campos = sorted(campos, key=lambda x: x[0])
        dimensiones_valores = {}
        dimensiones_keys = {
            "alto": ["ALTO", "HEIGHT", "ALTURA"],
            "ancho": ["ANCHO", "WIDTH"],
            "largo": ["LARGO", "LENGTH", "LONGITUD"],
            "peso": ["PESO", "WEIGHT"]
        }
        for _, attr in campos:
            aid = attr["id"]
            nombre = attr["name"]
            vtype = attr["value_type"]
            prev_val = st.session_state.get("ml_attrs", {}).get(aid, "")
            for k, keys in dimensiones_keys.items():
                if any(key in nombre.upper() or key in aid.upper() for key in keys):
                    val = st.number_input(nombre, key=f"ml_{aid}_edit", value=to_float(prev_val) if prev_val else 0.0)
                    ml_attrs[aid] = val
                    dimensiones_valores[k] = val
                    break
            else:
                if aid == "GTIN":
                    gtin_val = st.text_input("Código universal de producto (GTIN)", value=prev_val, key=f"ml_{aid}_edit")
                    ml_attrs[aid] = gtin_val
                elif aid == "EMPTY_GTIN_REASON":
                    opciones = [v["name"] for v in attr.get("values", [])]
                    ml_attrs[aid] = st.selectbox("Motivo por el que no tiene GTIN", opciones, index=opciones.index(prev_val) if prev_val in opciones else 0, key=f"ml_{aid}_edit")
                elif vtype == "boolean":
                    opt = ["Sí", "No"]
                    ml_attrs[aid] = st.selectbox(nombre, opt, index=opt.index(prev_val) if prev_val in opt else 0, key=f"ml_{aid}_edit")
                elif vtype == "list":
                    opt = [v["name"] for v in attr.get("values", [])]
                    ml_attrs[aid] = st.selectbox(nombre, opt if opt else ["-"], index=opt.index(prev_val) if prev_val in opt else 0, key=f"ml_{aid}_edit")
                elif vtype in ("number_unit", "number"):
                    ml_attrs[aid] = st.number_input(nombre, key=f"ml_{aid}_edit", value=to_float(prev_val) if prev_val else 0.0)
                else:
                    ml_attrs[aid] = st.text_input(nombre, value=prev_val, key=f"ml_{aid}_edit")
        st.session_state["ml_attrs"] = ml_attrs

        try:
            alto = float(dimensiones_valores.get("alto") or 0)
            ancho = float(dimensiones_valores.get("ancho") or 0)
            largo = float(dimensiones_valores.get("largo") or 0)
            peso = float(dimensiones_valores.get("peso") or 0)
        except Exception:
            alto = ancho = largo = peso = 0

        if not (alto and ancho and largo and peso):
            st.warning("Para calcular el costo de envío, asegúrate de completar alto, ancho, largo y peso en los atributos de ML.")
            dimensiones_str = ""
        else:
            dimensiones_str = f"{alto}x{ancho}x{largo},{peso}"
            st.success(f"Dimensiones para envío: {dimensiones_str}")
        st.session_state["dimensiones_str"] = dimensiones_str
    else:
        st.info("Selecciona un nombre de producto para detectar categoría.")

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
    "ganancia_facebook": str(ganancia_fb) if "ganancia_fb" in locals() and ganancia_fb is not None else None,
    "precio_mercado_libre": limpiar_valor(st.session_state.get("precio_mercado_libre")),
    "comision_mercado_libre": str(comision_ml),
    "envio_mercado_libre": limpiar_valor(st.session_state.get("envio_mercado_libre")),
    "ganancia_mercado_libre": str(ganancia_ml_estimada) if "ganancia_ml_estimada" in locals() and ganancia_ml_estimada is not None else None,
    "ganancia_mercado_libre_iva": f"{ganancia_ml_neta:.0f}" if "ganancia_ml_neta" in locals() and ganancia_ml_neta is not None else None,
    "precio_mercado_libre_30_desc": f"{precio_ml_30:.0f}" if "precio_ml_30" in locals() else None,
    "comision_mercado_libre_30_desc": str(comision_ml_30),
    "envio_mercado_libre_30_desc": "0",
    "ganancia_mercado_libre_30_desc": str(ganancia_ml_desc_estimada) if "ganancia_ml_desc_estimada" in locals() and ganancia_ml_desc_estimada is not None else None,
    "ganancia_mercado_libre_iva_30_desc": f"{ganancia_ml_desc_neta:.0f}" if "ganancia_ml_desc_neta" in locals() and ganancia_ml_desc_neta is not None else None,
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
    "ml_cat_id": ml_cat_id,
    "ml_listing_type": tipo_pub,
    "ml_attrs": st.session_state.get("ml_attrs", {})
}

if st.button("💾 Actualizar Producto"):
    try:
        nuevos_limpios = filtrar_campos(nuevos)
        if not nuevos_limpios:
            st.error("❌ No hay datos para actualizar.")
        else:
            doc_ref.update(nuevos_limpios)
            st.success(f"✅ Producto actualizado correctamente.")
            st.balloons()
            time.sleep(1)
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error actualizando producto: {e}")

if st.button("🗑️ Eliminar Producto", type="primary"):
    st.session_state["confirm_delete"] = True

if st.session_state.get("confirm_delete"):
    st.warning("¿Estás seguro de que quieres eliminar este producto? Esta acción no se puede deshacer.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Sí, eliminar DEFINITIVAMENTE"):
            try:
                doc_ref.delete()
                st.success("Producto eliminado correctamente.")
                st.session_state["confirm_delete"] = False
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error eliminando producto: {e}")
    with col2:
        if st.button("❌ Cancelar"):
            st.session_state["confirm_delete"] = False

st.markdown("</div>", unsafe_allow_html=True)
