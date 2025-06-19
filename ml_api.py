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
    # Si está cacheado y no expiró, úsalo
    if TOKEN_CACHE.exists():
        d = json.loads(TOKEN_CACHE.read_text())
        if d.get("expires_at", 0) > datetime.datetime.now().timestamp() + 60:
            return d["access_token"]
    # Si no, refresca
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

# ==== AUTOCOMPLETAR CATEGORÍAS ====
def suggest_categories(title: str, site: str = "MLC", limit: int = 5):
    if not title.strip():
        return []
    q = urllib.parse.quote(title.strip())
    url = (f"https://api.mercadolibre.com/sites/{site}/domain_discovery/search?limit={limit}&q={q}")
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

# ==== CAMPOS DE CATEGORÍA: OBLIGATORIOS + OPCIONALES ====
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
            # Si MercadoLibre falla, guardamos error mínimo para no reventar
            return []
    # A veces MercadoLibre responde con {"message": "Forbidden"} (dict) → evitamos crash
    if not isinstance(data, list):
        return []
    return data

# ==== EXTRA: SOLO OBLIGATORIOS ====
def get_required_attrs(cat_id: str):
    data = get_all_attrs(cat_id)
    return [a for a in data if a.get("tags", {}).get("required")]

# ==== OBTENER NOMBRE COMPLETO DE CATEGORÍA ====
def get_categoria_nombre_ml(cat_id):
    """
    Devuelve el nombre completo de la categoría de ML (incluyendo subcategorías), por ejemplo:
    "Juguetes › Peluches › Animales de peluche"
    """
    if not cat_id:
        return ""
    url = f"https://api.mercadolibre.com/categories/{cat_id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            path = data.get("path_from_root", [])
            return " › ".join([n["name"] for n in path])
    except Exception as e:
        pass
    return ""

# ==== OBTENER COMISIÓN Y COSTO FIJO DE LA CATEGORÍA ====
def get_comision_categoria_ml(cat_id, precio, tipo="clásico"):
    """
    Devuelve (porcentaje_comision, costo_fijo, tipo_tarifa)
    - porcentaje_comision: Ej: 13
    - costo_fijo: Ej: 700 o 1000 según precio (int)
    - tipo_tarifa: "clásico" o "premium"
    """
    if not cat_id or not precio:
        return 0, 0, tipo
    # Llamada a la API de MercadoLibre para buscar las tarifas de la categoría
    url = f"https://api.mercadolibre.com/sites/MLC/listing_prices"
    params = {
        "price": float(precio),
        "category_id": cat_id,
        "listing_type_id": "gold_special" if tipo.lower() == "premium" else "gold_pro"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.ok:
            data = resp.json()
            # MercadoLibre devuelve una lista de tipos de publicación
            for tarifa in data:
                if tarifa.get("listing_type_id") == params["listing_type_id"]:
                    commission = tarifa.get("sale_fee_amount", 0)
                    percent = tarifa.get("sale_fee", 0) * 100  # Ejemplo: 0.13 → 13
                    costo_fijo = tarifa.get("fixed_fee_amount", 0)
                    # Si faltan datos, los calculamos igual
                    return percent, costo_fijo, tipo
    except Exception:
        pass
    # Fallback: REGLA BÁSICA (ajusta a Chile)
    precio = float(precio)
    percent = 13 if tipo.lower() == "clásico" else 17  # Estos son valores ejemplo
    costo_fijo = 1000 if precio >= 9990 else 700
    return percent, costo_fijo, tipo
