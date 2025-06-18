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

rol_usuario = obtener_rol()  # "admin" o "vendedor"

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

rol_usuario = obtener_rol()
if rol_usuario != "admin":
    st.error("Acceso solo para administradores.")
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
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='container'>", unsafe_allow_html=True)

# --- TÍTULO ---
st.markdown("<h1 style='text-align: center;'>✏️ Editar producto</h1>", unsafe_allow_html=True)
st.markdown(f"<h3 style='text-align: center; color: #205ec5;'>🆔 ID producto: {a_str(producto.get('id',''))}</h3>", unsafe_allow_html=True)

# --- Progreso del formulario ---
obligatorios_ids = [
    "codigo_barra", "codigo_minimo", "proveedor", "nombre_producto", "categoria", "marca",
    "descripcion", "estado", "precio_facebook", "comision_vendedor_facebook", "precio_compra"
]

# --- Precarga datos SOLO la primera vez por producto ---
if "form_precargado" not in st.session_state:
    st.session_state.codigo_barra = a_str(producto.get("codigo_barra", ""))
    st.session_state.codigo_minimo = a_str(producto.get("codigo_minimo", ""))
    st.session_state.proveedor = a_str(producto.get("proveedor", ""))
    st.session_state.nombre_producto = a_str(producto.get("nombre_producto", ""))
    st.session_state.categoria = a_str(producto.get("categoria", ""))
    st.session_state.marca = a_str(producto.get("marca", ""))
    st.session_state.descripcion = a_str(producto.get("descripcion", ""))
    st.session_state.estado = a_str(producto.get("estado", ""))
    st.session_state.imagen_principal_url = a_str(producto.get("imagen_principal_url", ""))
    st.session_state.imagenes_secundarias_url = a_str(producto.get("imagenes_secundarias_url", ""))
    st.session_state.etiquetas = a_str(producto.get("etiquetas", ""))
    st.session_state.foto_proveedor = a_str(producto.get("foto_proveedor", ""))
    st.session_state.precio_compra = a_str(producto.get("precio_compra", ""))
    st.session_state.precio_facebook = a_str(producto.get("precio_facebook", ""))
    st.session_state.comision_vendedor_facebook = a_str(producto.get("comision_vendedor_facebook", ""))
    st.session_state.precio_mayor_3 = a_str(producto.get("precio_mayor_3", ""))
    st.session_state.precio_mercado_libre = a_str(producto.get("precio_mercado_libre", ""))
    st.session_state.comision_mercado_libre = a_str(producto.get("comision_mercado_libre", ""))
    st.session_state.envio_mercado_libre = a_str(producto.get("envio_mercado_libre", ""))
    st.session_state.comision_mercado_libre_30_desc = a_str(producto.get("comision_mercado_libre_30_desc", ""))
    st.session_state.envio_mercado_libre_30_desc = a_str(producto.get("envio_mercado_libre_30_desc", ""))
    st.session_state.stock = a_str(producto.get("stock", ""))
    st.session_state.mostrar_catalogo = a_str(producto.get("mostrar_catalogo", ""))
    st.session_state.id_publicacion_mercado_libre = a_str(producto.get("id_publicacion_mercado_libre", ""))
    st.session_state.link_publicacion_1 = a_str(producto.get("link_publicacion_1", ""))
    st.session_state.link_publicacion_2 = a_str(producto.get("link_publicacion_2", ""))
    st.session_state.link_publicacion_3 = a_str(producto.get("link_publicacion_3", ""))
    st.session_state.link_publicacion_4 = a_str(producto.get("link_publicacion_4", ""))
    st.session_state.cantidad_vendida = a_str(producto.get("cantidad_vendida", ""))
    st.session_state.ultima_entrada = a_str(producto.get("ultima_entrada", ""))
    st.session_state.ultima_salida = a_str(producto.get("ultima_salida", ""))
    st.session_state.form_precargado = True

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

# --- BOTÓN ACTUALIZAR ---
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
    "comision_mercado_libre": limpiar_valor(st.session_state.get("comision_mercado_libre")),
    "envio_mercado_libre": limpiar_valor(st.session_state.get("envio_mercado_libre")),
    "ganancia_mercado_libre": str(ganancia_ml_estimada) if "ganancia_ml_estimada" in locals() and ganancia_ml_estimada is not None else None,
    "ganancia_mercado_libre_iva": f"{ganancia_ml_neta:.0f}" if "ganancia_ml_neta" in locals() and ganancia_ml_neta is not None else None,
    "precio_mercado_libre_30_desc": f"{precio_ml_desc:.0f}" if "precio_ml_desc" in locals() else None,
    "comision_mercado_libre_30_desc": limpiar_valor(st.session_state.get("comision_mercado_libre_30_desc")),
    "envio_mercado_libre_30_desc": limpiar_valor(st.session_state.get("envio_mercado_libre_30_desc")),
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
}

if st.button("💾 Actualizar Producto"):
    try:
        nuevos_limpios = filtrar_campos(nuevos)
        if not nuevos_limpios:
            st.error("❌ No hay cambios para actualizar (diccionario vacío).")
        else:
            try:
                doc_ref.update(nuevos_limpios)
                st.success(f"✅ Producto {a_str(producto.get('id',''))} actualizado correctamente.")
                st.balloons()
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error actualizando producto: {e}")
    except Exception as e:
        st.error(f"❌ Error actualizando producto: {e}")

# --- BOTÓN DEBUG: UPDATE CAMPO POR CAMPO ---
if st.button("🔍 Test update campo por campo (debug)"):
    nuevos_limpios = filtrar_campos(nuevos)
    for k, v in nuevos_limpios.items():
        try:
            doc_ref.update({k: v})
            st.success(f"Campo '{k}' actualizado OK.")
        except Exception as e:
            st.error(f"Campo '{k}' falló: {e}")

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
# TAB extra: MercadoLibre
with tabs[-1]:  # último tab
    st.subheader("Atributos MercadoLibre")
    ml_cat_id = st.text_input("ID categoría ML", value=st.session_state.get("ml_cat_id",""), key="ml_cat_id")
    req_attrs = []
    if ml_cat_id:
        try:
            req_attrs = ml_api.get_required_attrs(ml_cat_id)
        except Exception as e:
            st.warning(f"No se pudieron obtener atributos: {e}")
    ml_attr_vals = st.session_state.get("ml_attrs", {})
    for attr in req_attrs:
        aid = attr["id"]; name = attr["name"]
        vtype = attr["value_type"]
        default_val = ml_attr_vals.get(aid,"")
        if vtype in ("boolean"):
            opt = ["Sí", "No"]
            ml_attr_vals[aid] = st.selectbox(name, opt, key=f"ml_{aid}_edit", index=opt.index(default_val) if default_val in opt else 0)
        elif vtype in ("list",):
            opts = [v["name"] for v in attr.get("values",[])]
            idx_def = opts.index(default_val) if default_val in opts else 0
            ml_attr_vals[aid] = st.selectbox(name, opts if opts else ["-"], key=f"ml_{aid}_edit", index=idx_def)
        else:
            ml_attr_vals[aid] = st.text_input(name, value=default_val, key=f"ml_{aid}_edit")
    st.session_state["ml_attrs"] = ml_attr_vals