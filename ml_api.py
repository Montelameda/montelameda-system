import requests
import json
import pathlib
import datetime
import urllib.parse

CACHE_TTL_HRS = 24
CACHE_DIR = pathlib.Path(".ml_cache")
CACHE_DIR.mkdir(exist_ok=True)

# ==== CREDENCIALES ML ====
ML_CLIENT_ID = "264097672348150"
ML_CLIENT_SECRET = "oCouItXpao4bYX1GZ0ZTAC16brpqLgkP"
ML_REFRESH_TOKEN = "TG-68530d69b78f1e0001a8d29e-2227856718"
TOKEN_CACHE = CACHE_DIR / "ml_token.json"

# ==== TOKEN HANDLER (Solo para endpoints privados) ====
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

# ==== AUTOCOMPLETAR CATEGORÍAS (Público) ====
def suggest_categories(title: str, site: str = "MLC", limit: int = 5):
    if not title.strip():
        return []
    q = urllib.parse.quote(title.strip())
    url = (f"https://api.mercadolibre.com/sites/{site}/domain_discovery/search?limit={limit}&q={q}")
    try:
        data = requests.get(url, timeout=10).json()
    except Exception:
        return []
    out = []
    for item in data:
        cid = item["category_id"]
        try:
            resp = requests.get(f"https://api.mercadolibre.com/categories/{cid}", timeout=10)
            path = resp.ok and resp.json().get("path_from_root", [])
            name = " › ".join(n["name"] for n in path) if path else item["domain_name"]
        except Exception:
            name = item["domain_name"]
        out.append((cid, name))
    return out

# ==== OBTÉN EL NOMBRE Y RUTA DE CATEGORÍA (Público) ====
def get_categoria_nombre_ml(category_id):
    url = f"https://api.mercadolibre.com/categories/{category_id}"
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            path = " > ".join([p["name"] for p in data.get("path_from_root", [])])
            return f"{category_id} - {path}"
    except Exception as e:
        print(f"[ml_api/get_categoria_nombre_ml] Error: {e}")
    return category_id

# ==== OBTÉN TODOS LOS ATRIBUTOS DE UNA CATEGORÍA (Privado, usa token si la API lo exige) ====
def get_all_attrs(cat_id: str):
    if not cat_id:
        return []
    fp = CACHE_DIR / f"attrs_{cat_id}.json"
    data = _cached(fp)
    if data is None:
        # Intenta primero SIN token (endpoint público)
        url = f"https://api.mercadolibre.com/categories/{cat_id}/attributes"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            fp.write_text(json.dumps(data, ensure_ascii=False))
        else:
            # Si ML exige token o rechaza, prueba CON token
            try:
                access_token = get_ml_token()
                headers = {"Authorization": f"Bearer {access_token}"}
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    fp.write_text(json.dumps(data, ensure_ascii=False))
                else:
                    return []
            except Exception as e:
                print(f"[ml_api/get_all_attrs] Error (con token): {e}")
                return []
    # Puede devolver dict de error, por seguridad:
    if not isinstance(data, list):
        return []
    return data

# ==== EXTRA: SOLO ATRIBUTOS OBLIGATORIOS ====
def get_required_attrs(cat_id: str):
    data = get_all_attrs(cat_id)
    return [a for a in data if a.get("tags", {}).get("required")]

# ==== CONSULTA COMISIÓN (%) Y COSTO FIJO (Público, no necesita token) ====
def get_comision_categoria_ml(category_id, price, listing_type_id="gold_special"):
    try:
        url = f"https://api.mercadolibre.com/categories/{category_id}/listing_types/{listing_type_id}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            porcentaje = float(data.get("sale_fee_amount", 0)) * 100 if data.get("sale_fee_amount") else 13.0
            costo_fijo = int(data.get("sale_fee_fixed_amount", 0)) if data.get("sale_fee_fixed_amount") else (1000 if float(price) >= 9990 else 700)
            return porcentaje, costo_fijo
    except Exception as e:
        print(f"[ml_api/get_comision_categoria_ml] Error: {e}")
    porcentaje = 13.0
    costo_fijo = 1000 if float(price) >= 9990 else 700
    return porcentaje, costo_fijo

# ==== CONSULTA ENVÍO GRATIS Y COSTO (Público, no necesita token) ====
def get_envio_gratis_ml(category_id, price, dimensions="10x10x10,1", zip_code="8320000", listing_type_id="gold_special"):
    url = "https://api.mercadolibre.com/sites/MLC/shipping_options"
    params = {
        "dimensions": dimensions,
        "zip_code": zip_code,
        "item_price": price,
        "category_id": category_id,
        "listing_type_id": listing_type_id
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            opciones = data.get("options", [])
            for op in opciones:
                if op.get("free_shipping"):
                    return True, int(op.get("list_cost", 0))
            if opciones:
                return False, int(opciones[0].get("list_cost", 0))
    except Exception as e:
        print(f"[ml_api/get_envio_gratis_ml] Error: {e}")
    return False, 0

# ==== PUBLICAR/EDITAR PRODUCTO EN MERCADOLIBRE (usa token, cuando lo implementes) ====
def publicar_producto_ml(datos):
    """
    Ejemplo de cómo usar el token para publicar.
    (No implementado aquí, pero listo para cuando lo uses).
    """
    access_token = get_ml_token()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    url = "https://api.mercadolibre.com/items"
    resp = requests.post(url, headers=headers, json=datos)
    return resp.json()

# ==== MÁS UTILIDADES QUE NECESITES AQUÍ... ====
