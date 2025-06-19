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

# ==== FALLBACK: DICCIONARIO DE COMISIONES Y COSTOS FIJOS ====
# Actualiza este diccionario si quieres, pero el sistema intenta usar siempre el API
COMISIONES_CATEGORIAS_CHILE = {
    # cat_id: { "clasico": (porcentaje, costo_fijo), "premium": (porcentaje, costo_fijo) }
    "MLC1166": {"clasico": (13.0, None), "premium": (16.0, None)}, # Peluches/Juguetes ejemplo
    "MLC1574": {"clasico": (13.0, None), "premium": (16.0, None)}, # Herramientas ejemplo
    # Agrega tus categorías manualmente si quieres para pruebas
}

# ==== FUNCIÓN PARA COMISIÓN SEGÚN CATEGORÍA, PRECIO Y TIPO PUBLICACIÓN ====
def get_comision_categoria_ml(cat_id: str, precio: float, tipo_pub: str):
    """
    Devuelve el porcentaje y costo fijo de comisión para MercadoLibre Chile,
    usando el endpoint oficial. Si falla, usa el diccionario de respaldo.
    """
    tipo_pub = tipo_pub.lower()
    # Mapear tipo de publicación a listing_type_id de ML Chile
    listing_type_id = "gold_pro" if tipo_pub in ["clásico", "clasico"] else "gold_special"
    try:
        url = (
            f"https://api.mercadolibre.com/sites/MLC/listing_prices"
            f"?price={int(precio)}&category_id={cat_id}&listing_type_id={listing_type_id}"
        )
        resp = requests.get(url, timeout=6)
        if resp.ok:
            data = resp.json()
            if isinstance(data, list) and data:
                cost = data[0]
                sale_fee = float(cost.get("sale_fee_amount", 0))
                porcentaje = round(100 * sale_fee / float(precio), 2) if precio > 0 else 0.0
                costo_fijo = 0  # Generalmente todo va al porcentaje, pero puedes adaptarlo
                return porcentaje, costo_fijo
    except Exception as e:
        print(f"[WARN] Error al consultar comisión exacta ML: {e}")

    # Fallback: tu tabla manual
    porcentaje = 13.0
    if cat_id in COMISIONES_CATEGORIAS_CHILE and tipo_pub in COMISIONES_CATEGORIAS_CHILE[cat_id]:
        porcentaje = COMISIONES_CATEGORIAS_CHILE[cat_id][tipo_pub][0]
    elif tipo_pub == "premium":
        porcentaje = 16.0
    else:
        porcentaje = 13.0
    costo_fijo = 700 if precio <= 9990 else 1000
    return porcentaje, costo_fijo

# ==== PUBLICAR PRODUCTO (FUTURO) ====
def publicar_producto_ml(datos_producto):
    # Aquí va tu integración de publicación automática (cuando la necesites)
    raise NotImplementedError("Publicación automática aún no implementada")
