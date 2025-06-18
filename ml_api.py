# ml_api.py  – Utilidades MercadoLibre
# -------------------------------------
# · suggest_categories()  → [(category_id, nombre)]
# · get_all_attrs()  → lista de TODOS los atributos de la categoría
# Usa caché local en .ml_cache/ para no reventar la API.

import requests
import json
import pathlib
import datetime
import urllib.parse

CACHE_TTL_HRS = 24          # refrescamos cada 24 h
CACHE_DIR = pathlib.Path(".ml_cache")
CACHE_DIR.mkdir(exist_ok=True)

# ---------- helper de caché ----------
def _cached(fp: pathlib.Path):
    """Devuelve JSON cacheado o None si no existe / expiró / está corrupto."""
    if not fp.exists():
        return None
    age = (datetime.datetime.now() -
           datetime.datetime.fromtimestamp(fp.stat().st_mtime)).total_seconds()
    if age > CACHE_TTL_HRS * 3600:
        return None
    try:
        return json.loads(fp.read_text())
    except json.JSONDecodeError:
        return None

# ---------- AUTOCOMPLETAR CATEGORÍAS ----------
def suggest_categories(title: str, site: str = "MLC", limit: int = 5):
    """
    Devuelve lista [(cat_id, nombre_mostrable)] ordenada por relevancia.
    Si /categories/<id> responde 403/429/5xx o sin 'path_from_root',
    caemos al domain_name para evitar crasheos.
    """
    if not title.strip():
        return []

    q = urllib.parse.quote(title.strip())
    url = (f"https://api.mercadolibre.com/sites/{site}"
           f"/domain_discovery/search?limit={limit}&q={q}")

    try:
        data = requests.get(url, timeout=10).json()
    except requests.exceptions.RequestException:
        return []

    out = []
    for item in data:
        cid = item["category_id"]

        # Intentamos sacar la ruta completa (puede dar 403 en Streamlit Cloud)
        try:
            resp = requests.get(f"https://api.mercadolibre.com/categories/{cid}",
                                timeout=10)
            path = resp.ok and resp.json().get("path_from_root", [])
            name = " › ".join(n["name"] for n in path) if path else item["domain_name"]
        except requests.exceptions.RequestException:
            name = item["domain_name"]

        out.append((cid, name))

    return out

# ---------- TODOS LOS ATRIBUTOS DE LA CATEGORÍA ----------
def get_all_attrs(cat_id: str):
    """
    Devuelve TODOS los atributos de la categoría (no solo los obligatorios).
    """
    if not cat_id:
        return []

    fp = CACHE_DIR / f"attrs_{cat_id}.json"
    data = _cached(fp)

    if data is None:
        try:
            url = f"https://api.mercadolibre.com/categories/{cat_id}/attributes"
            data = requests.get(url, timeout=10).json()
            fp.write_text(json.dumps(data, ensure_ascii=False))
        except requests.exceptions.RequestException:
            return []

    if not isinstance(data, list):
        return []

    return data  # <-- Devuelve todos los atributos, sin filtrar
