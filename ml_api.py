# ml_api.py – Utilidades MercadoLibre Chile (MLC)
import requests
import json
import pathlib
import datetime
import urllib.parse

CACHE_TTL_HRS = 24
CACHE_DIR = pathlib.Path(".ml_cache")
CACHE_DIR.mkdir(exist_ok=True)

# ==== CONFIGURA TUS CREDENCIALES ====
ML_CLIENT_ID = "264097672348150"
ML_CLIENT_SECRET = "oCouItXpao4bYX1GZ0ZTAC16brpqLgkP"
ML_REFRESH_TOKEN = "TG-68530d69b78f1e0001a8d29e-2227856718"

TOKEN_CACHE = CACHE_DIR / "ml_token.json"

# ==== TOKEN HANDLER ====
def get_ml_token():
    if TOKEN_CACHE.exists():
        d = json.loads(TOKEN_CACHE.read_text())
        if d.get("expires_at", 0) > datetime.datetime.now().timestamp() + 60:
            return d["access_token"]
    resp = requests.post("https://api.mercadolibre.com/oauth/token", data={
        "grant_type": "refresh_token",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": ML_REFRESH_TOKEN
    })
    if resp.ok:
        data = resp.json()
        expires_at = datetime.datetime.now().timestamp() + int(data["expires_in"])
        TOKEN_CACHE.write_text(json.dumps({
            "access_token": data["access_token"],
            "expires_at": expires_at
        }))
        return data["access_token"]
    else:
        raise RuntimeError(f"Error renovando token ML: {resp.text}")

# ==== CACHÉ GENÉRICO ====
def _cached(fp: pathlib.Path):
    if not fp.exists():
        return None
    age = (datetime.datetime.now() - datetime.datetime.fromtimestamp(fp.stat().st_mtime)).total_seconds()
    if age > CACHE_TTL_HRS * 3600:
        return None
    try:
        return json.loads(fp.read_text())
    except json.JSONDecodeError:
        return None

# ==== SUGERIR CATEGORÍAS POR NOMBRE ====
def suggest_categories(title: str, site: str = "MLC", limit: int = 5):
    if not title.strip():
        return []
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

# ==== OBTENER NOMBRE CATEGORÍA COMPLETO ====
def get_categoria_nombre_ml(cat_id: str):
    if not cat_id:
        return ""
    url = f"https://api.mercadolibre.com/categories/{cat_id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.ok:
            path = resp.json().get("path_from_root", [])
            if path:
                return " › ".join(n["name"] for n in path)
    except:
        pass
    return cat_id

# ==== OBTENER ATRIBUTOS DE CATEGORÍA ====
def get_all_attrs(cat_id: str):
    if not cat_id:
        return []
    fp = CACHE_DIR / f"attrs_{cat_id}.json"
    data = _cached(fp)
    if data is None:
        access_token = get_ml_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://api.mercadolibre.com/categories/{cat_id}/attributes"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            fp.write_text(json.dumps(data, ensure_ascii=False))
        else:
            return []
    if not isinstance(data, list):
        return []
    return data

def get_required_attrs(cat_id: str):
    data = get_all_attrs(cat_id)
    return [a for a in data if a.get("tags", {}).get("required")]

# ==== COMISIÓN REAL DESDE API MERCADOLIBRE (con costo fijo MLC) ====
def get_comision_categoria_ml(cat_id: str, precio: float, tipo_pub: str):
    """
    Trae la comisión REAL desde la API autenticada de MercadoLibre para tu cuenta y categoría.
    Devuelve el porcentaje real y el costo fijo que aplica en ML Chile.
    """
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
    dimensions,  # Ej: '30x20x10,800' (alto x ancho x largo, peso en gramos)
    category_id,
    listing_type_id,
    condition="new"
):
    """
    Consulta el costo estimado de envío para ML Chile, usando tu cuenta.
    """
    user_id = "2227856718"  # Tu User ID fijo
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

# ==== PUBLICAR PRODUCTO (FUTURO) ====
def publicar_producto_ml(datos_producto):
    raise NotImplementedError("Publicación automática aún no implementada")
