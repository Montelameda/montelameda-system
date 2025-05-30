import requests
from PIL import Image
from io import BytesIO
import zipfile

colbtn1, colbtn2, colbtn3 = st.columns([1,1,1], gap="medium")

with colbtn1:
    if st.button("⬅️ Volver al catálogo"):
        st.session_state["go_to"] = "catalogo"
        st.rerun()
with colbtn2:
    if st.button("✏️ Editar producto"):
        st.query_params["producto_id"] = producto_id
        st.switch_page("pages/editar_producto.py")

def exportar_producto(producto):
    titulo = producto.get("nombre_producto", "Sin_titulo")
    precio_fb = producto.get("precio_facebook", "Sin_precio")
    descripcion = producto.get("descripcion", "Sin_descripcion")
    etiquetas = producto.get("etiquetas", "Sin_etiquetas")
    
    texto_info = f"""TÍTULO: {titulo}
PRECIO FACEBOOK: {precio_fb}
DESCRIPCIÓN:
{descripcion}

ETIQUETAS:
{etiquetas}
"""

    urls = []
    if producto.get("imagen_principal_url"):
        urls.append(producto["imagen_principal_url"])
    if producto.get("imagenes_secundarias_url"):
        urls += [u.strip() for u in str(producto["imagenes_secundarias_url"]).split(",") if u.strip()]
    
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr("info.txt", texto_info)
        for idx, url in enumerate(urls):
            try:
                r = requests.get(url)
                img = Image.open(BytesIO(r.content))
                ext = img.format.lower() if img.format else "jpg"
                zip_file.writestr(f"imagen_{idx+1}.{ext}", r.content)
            except Exception as e:
                print(f"Error descargando imagen {url}: {e}")

    return zip_buffer.getvalue(), titulo

with colbtn3:
    zip_data, nombre_zip = exportar_producto(producto)
    st.download_button(
        label="⬇️ Exportar ZIP",
        data=zip_data,
        file_name=f"{nombre_zip.replace(' ', '_')}.zip",
        mime="application/zip"
    )

# ---- CABECERA: Nombre, ID y datos clave ----
st.markdown(f"<div class='product-title'>{producto.get('nombre_producto', 'Producto sin título')}</div>", unsafe_allow_html=True)
st.markdown(f'<div class="tag-id">ID: {producto.get("id", "—")}</div>', unsafe_allow_html=True)

# Datos clave pill-style debajo del ID
campos_cabecera = [
    ("proveedor", "Proveedor"),
    ("codigo_barra", "Código de barra"),
    ("codigo_minimo", "Código mínimo"),
    ("categoria", "Categoría"),
    ("marca", "Marca"),
]
pills_html = ""
for campo, label in campos_cabecera:
    valor = producto.get(campo, "")
    if tiene_valor(valor):
        pills_html += f"<div class='cat-marca-item'>{label}: {valor}</div>"
if pills_html:
    st.markdown(f"<div class='cat-marca-bar'>{pills_html}</div>", unsafe_allow_html=True)

# --------- GALERÍA VISUAL (SCROLL) ----------
imagenes = []
if "imagen_principal_url" in producto and tiene_valor(producto.get("imagen_principal_url")):
    portada = producto["imagen_principal_url"].strip()
    if portada:
        imagenes.append(portada)
if "imagenes_secundarias_url" in producto and tiene_valor(producto["imagenes_secundarias_url"]):
    urls = [u.strip() for u in str(producto["imagenes_secundarias_url"]).split(",") if u.strip()]
    urls = [u for u in urls if u and u not in imagenes]
    imagenes.extend(urls)
if imagenes:
    st.markdown("<div class='img-slider-scroll'>" + "".join([f"<img src='{u}' />" for u in imagenes]) + "</div>", unsafe_allow_html=True)

# ------ GRUPOS Y TABS ---------
FICHA_CAMPOS = [
    "nombre_producto", "descripcion", "ficha_tecnica", "etiquetas"
]
PRECIOS_SOCIAL = [
    "precio_compra", "precio_facebook", "comision_vendedor_facebook", "ganancia_facebook", "precio_mayor_3"
]
PRECIOS_ML_NORMAL = [
    "precio_mercado_libre", "comision_mercado_libre", "envio_mercado_libre", "ganancia_mercado_libre", "ganancia_mercado_libre_iva"
]
PRECIOS_ML_30 = [
    "precio_mercado_libre_30_desc", "comision_mercado_libre_30_desc", "envio_mercado_libre_30_desc", "ganancia_mercado_libre_30_desc", "ganancia_mercado_libre_iva_30_desc"
]
STOCK_PROVEEDOR = [
    "stock", "estado",
]
GRUPOS = {
    "Ficha": FICHA_CAMPOS,
    "Precios y Comisiones": PRECIOS_SOCIAL + PRECIOS_ML_NORMAL + PRECIOS_ML_30,
    "Stock y Proveedor": STOCK_PROVEEDOR,
}

CAMPOS_VENDEDOR = [
    "imagen_principal_url", "imagenes_secundarias_url", *FICHA_CAMPOS,
    *PRECIOS_SOCIAL, *PRECIOS_ML_NORMAL, *PRECIOS_ML_30, *STOCK_PROVEEDOR,
    "proveedor", "codigo_barra", "codigo_minimo", "categoria", "marca"
]
CAMPOS_TODOS = list(producto.keys())

if rol == "admin":
    campos_permitidos = CAMPOS_TODOS
else:
    campos_permitidos = [c for c in CAMPOS_VENDEDOR if c in producto]

tab_names = list(GRUPOS.keys())
if rol == "admin":
    internos = [k for k in campos_permitidos if k not in [c for group in GRUPOS.values() for c in group] and tiene_valor(producto.get(k, ""))]
    if internos:
        tab_names.append("Interno")

tabs = st.tabs(tab_names)

for i, grupo in enumerate(tab_names):
    with tabs[i]:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        if grupo == "Ficha":
            st.markdown(f"<h3 style='color:#223660;font-size:1.32rem;font-weight:800;margin-bottom:8px'>Descripción del Producto</h3>", unsafe_allow_html=True)
            desc = producto.get("descripcion", "")
            if "descripcion" in campos_permitidos and tiene_valor(desc):
                st.markdown(f"<div class='descripcion-ficha'>{desc}</div>", unsafe_allow_html=True)
            ficha_tecnica = producto.get("ficha_tecnica", "")
            if "ficha_tecnica" in campos_permitidos and tiene_valor(ficha_tecnica):
                st.markdown(f"<div class='ficha-tecnica-label'>FICHA TÉCNICA</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ficha-tecnica-block'>{ficha_tecnica}</div>", unsafe_allow_html=True)
            etiquetas = producto.get("etiquetas", "")
            if "etiquetas" in campos_permitidos and tiene_valor(etiquetas):
                st.markdown(f"<div class='field-label'>Etiquetas:</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ficha-texto'>{etiquetas}</div>", unsafe_allow_html=True)

        elif grupo == "Precios y Comisiones":
            # Redes sociales / Venta directa
            st.markdown("<div class='redes-titulo'><span class='red-ico'>💬</span>Redes sociales / Venta directa</div>", unsafe_allow_html=True)
            for campo in PRECIOS_SOCIAL:
                if campo not in campos_permitidos:
                    continue
                valor = producto.get(campo, "")
                if not tiene_valor(valor):
                    continue
                st.markdown(f"<div class='field-label'>{campo.replace('_',' ').capitalize()}:</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ficha-texto'>{valor}</div>", unsafe_allow_html=True)

            # Mercado Libre
            st.markdown("<div class='ml-titulo'><span class='ml-ico'>🟡</span>Mercado Libre</div>", unsafe_allow_html=True)
            for campo in PRECIOS_ML_NORMAL:
                if campo not in campos_permitidos:
                    continue
                valor = producto.get(campo, "")
                if not tiene_valor(valor):
                    continue
                st.markdown(f"<div class='field-label'>{campo.replace('_',' ').capitalize()}:</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ficha-texto'>{valor}</div>", unsafe_allow_html=True)

            # Mercado Libre con 30% desc.
            st.markdown("<div class='ml30-titulo'><span class='ml-ico'>🟡</span>Mercado Libre <span style='font-size:1.01rem;'>(con 30% desc.)</span></div>", unsafe_allow_html=True)
            for campo in PRECIOS_ML_30:
                if campo not in campos_permitidos:
                    continue
                valor = producto.get(campo, "")
                if not tiene_valor(valor):
                    continue
                st.markdown(f"<div class='field-label'>{campo.replace('_',' ').capitalize()}:</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ficha-texto'>{valor}</div>", unsafe_allow_html=True)

        elif grupo == "Stock y Proveedor":
            for campo in STOCK_PROVEEDOR:
                if campo not in campos_permitidos:
                    continue
                valor = producto.get(campo, "")
                if not tiene_valor(valor):
                    continue
                st.markdown(f"<div class='field-label'>{campo.replace('_',' ').capitalize()}:</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ficha-texto'>{valor}</div>", unsafe_allow_html=True)
        elif grupo == "Interno":
            for campo in internos:
                valor = producto.get(campo, "")
                if not tiene_valor(valor):
                    continue
                st.markdown(f"<div class='field-label'>{campo.replace('_',' ').capitalize()}:</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='ficha-texto'>{valor}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

if rol == "admin":
    st.caption(f"ID de Firebase: {producto_id}")
