import json
import pathlib
import datetime
import urllib.parse

# ==== CONFIGURA TUS CREDENCIALES ====
# --- CONFIG (coloca tus credenciales si necesitas token, pero para predecir categoría NO pide token)
ML_CLIENT_ID = "264097672348150"
ML_CLIENT_SECRET = "oCouItXpao4bYX1GZ0ZTAC16brpqLgkP"
ML_REFRESH_TOKEN = "TG-68530d69b78f1e0001a8d29e-2227856718"

# ==== TOKEN HANDLER ====
TOKEN_CACHE = pathlib.Path(".ml_token.json")

def get_ml_token():
@@ -34,153 +32,23 @@ def get_ml_token():
    else:
        raise RuntimeError(f"Error renovando token ML: {resp.text}")

# ==== SUGERIR CATEGORÍAS POR NOMBRE (AUTODETECCIÓN) ====
def suggest_categories(title: str, site: str = "MLC", limit: int = 5):
    q = urllib.parse.quote(title.strip())
    url = f"https://api.mercadolibre.com/sites/{site}/domain_discovery/search?limit={limit}&q={q}"
    try:
        data = requests.get(url, timeout=10).json()
    except requests.exceptions.RequestException:
        return []
    out = []
    for item in data:
        cid = item["category_id"]
        try:
            resp = requests.get(f"https://api.mercadolibre.com/categories/{cid}", timeout=10)
            path = resp.ok and resp.json().get("path_from_root", [])
            name = " › ".join(n["name"] for n in path) if path else item["domain_name"]
        except requests.exceptions.RequestException:
            name = item["domain_name"]
        out.append((cid, name))
    return out

# ==== OBTENER TODOS LOS ATRIBUTOS DE UNA CATEGORÍA ====
def get_all_attrs(cat_id: str):
    url = f"https://api.mercadolibre.com/categories/{cat_id}/attributes"
    try:
        res = requests.get(url)
        res.raise_for_status()
        return res.json()
    except Exception:
        return []

# ==== SABER SI UN ATRIBUTO ES OBLIGATORIO SEGÚN DOC ML ====
def es_obligatorio_ml(attr):
    tags = attr.get("tags", {})
    return tags.get("required") or tags.get("new_required") or tags.get("conditional_required")

# ==== PUBLICAR PRODUCTO EN MERCADO LIBRE ====
def publicar_producto_ml(datos_producto):
    access_token = get_ml_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "title": datos_producto["nombre_producto"],
        "category_id": datos_producto["ml_cat_id"],
        "price": float(datos_producto["precio_mercado_libre"]),
        "currency_id": "CLP",
        "available_quantity": int(datos_producto["stock"]),
        "listing_type_id": "gold_special" if datos_producto.get("ml_listing_type", "clasico") in ["clásico", "clasico"] else "gold_pro",
        "condition": "new" if datos_producto.get("estado", "").lower() == "nuevo" else "used",
        "pictures": [{"source": datos_producto["imagen_principal_url"]}] if datos_producto.get("imagen_principal_url") else [],
        "description": {"plain_text": datos_producto["descripcion"]},
        "attributes": [
            {"id": k, "value_name": str(v)}
            for k, v in datos_producto.get("ml_attrs", {}).items() if v
        ]
    }
    resp = requests.post(
        "https://api.mercadolibre.com/items",
        headers=headers,
        data=json.dumps(payload)
    )
    if not resp.ok:
        raise Exception(f"Error publicando en ML: {resp.text}")
# --- DETECTAR CATEGORÍA COMO EN LA DOC OFICIAL ---
def predecir_categoria(nombre_producto, site_id="MLC"):
    params = {"q": nombre_producto, "limit": 1}
    url = f"https://api.mercadolibre.com/sites/{site_id}/domain_discovery/search"
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data:
        cat_id = data[0].get("category_id")
        dom_id = data[0].get("domain_id")
        atributos = data[0].get("attributes", [])
        return cat_id, dom_id, atributos
    return None, None, []

# --- OBTENER TODOS LOS ATRIBUTOS DE LA CATEGORÍA ---
def obtener_atributos_categoria(category_id):
    url = f"https://api.mercadolibre.com/categories/{category_id}/attributes"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

# ==== EDITAR PRODUCTO EN MERCADO LIBRE ====
def editar_producto_ml(id_ml, datos_producto):
    access_token = get_ml_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "title": datos_producto["nombre_producto"],
        "price": float(datos_producto["precio_mercado_libre"]),
        "available_quantity": int(datos_producto["stock"]),
        # Puedes agregar más campos editables aquí si quieres
    }
    resp = requests.put(
        f"https://api.mercadolibre.com/items/{id_ml}",
        headers=headers,
        data=json.dumps(payload)
    )
    if not resp.ok:
        raise Exception(f"Error editando en ML: {resp.text}")
    return resp.json()

# ==== COMISIÓN REAL DESDE API MERCADOLIBRE (con costo fijo MLC) ====
def get_comision_categoria_ml(cat_id: str, precio: float, tipo_pub: str):
    tipo_pub = tipo_pub.lower()
    listing_type_id = "gold_special" if tipo_pub in ["clásico", "clasico"] else "gold_pro"
    access_token = get_ml_token()
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    porcentaje = 0.0
    try:
        url = (
            f"https://api.mercadolibre.com/sites/MLC/listing_prices"
            f"?price={int(precio)}&category_id={cat_id}"
        )
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.ok:
            data = resp.json()
            for opt in data:
                if opt.get("listing_type_id", "") == listing_type_id:
                    sale_details = opt.get("sale_fee_details", {})
                    porcentaje = float(sale_details.get("percentage_fee", 0))
                    break
    except Exception as e:
        print(f"[WARN] Error consultando comisión ML: {e}")
    # ---- COSTO FIJO CHILE MANUAL ----
    if precio < 9990:
        costo_fijo = 700
    else:
        costo_fijo = 1000
    return porcentaje, costo_fijo

# ==== COSTO DE ENVÍO AUTOMÁTICO (ML CHILE) ====
def get_shipping_cost_mlc(
    item_price,
    dimensions,
    category_id,
    listing_type_id,
    condition="new"
):
    user_id = "2227856718"  # <-- Cambia por tu user_id si es necesario
    access_token = get_ml_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    url = (
        f"https://api.mercadolibre.com/users/{user_id}/shipping_options/free"
        f"?dimensions={dimensions}&verbose=true"
        f"&item_price={int(item_price)}"
        f"&listing_type_id={listing_type_id}"
        f"&category_id={category_id}"
        f"&condition={condition}"
        f"&mode=me2"
    )
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.ok:
        data = resp.json()
        try:
            cheapest = min(data["options"], key=lambda o: o["list_cost"])
            costo_envio = cheapest["list_cost"]
            return costo_envio, cheapest
        except Exception as e:
            print(f"Error analizando opciones de envío: {e}")
            return 0, {}
    else:
        print("Error en consulta de envío:", resp.text)
        return 0, {}
