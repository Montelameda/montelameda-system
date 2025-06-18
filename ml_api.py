# ml_api.py  – Utilidades Mercado Libre
# -------------------------------------
# • suggest_categories()  →  [(cat_id, nombre)]
# • get_required_attrs()  →  lista de atributos obligatorios
# Incluye caché local en .ml_cache/  para no saturar la API.

import requests
import json
import pathlib
import datetime
import urllib.parse

CACHE_TTL_HRS = 24
CACHE_DIR = pathlib.Path(".ml_cache")
CACHE_DIR.mkdir(exist_ok=True)


# ---------- helpers de caché ----------
def _cached(fp: pathlib.Path):
    """Devuelve el JSON cacheado o None si no existe / está vencido."""
    if not fp.exists():
        return None
    age = (datetime.datetime.now() -
           datetime.datetime.fromtimestamp(fp.stat().st_mtime)).total_seconds()
    if age > CACHE_TTL_HRS * 3600:
        return None
    return json.loads(fp.read_text())


# ---------- AUTOCOMPLETAR CATEGORÍAS ----------
def suggest_categories(title: str, site: str = "MLC", limit: int = 5):
    """
    Devuelve lista de tuplas (category_id, nombre_mostrable) ordenadas por relevancia.
    Si la API de categorías devuelve 403/429/5xx u omite 'path_from_root',
    usamos domain_name como fallback para evitar KeyError.
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

        # Intentamos ruta completa (puede fallar con 403)
        try:
            resp = requests.get(
                f"https://api.mercadolibre.com/categories/{cid}", timeout=10
            )
            path = resp.ok and resp.json().get("path_from_root", [])
            name = " › ".join(n["name"] for n in path) if path else item["domain_name"]
        except requests.exceptions.RequestException:
            name = item["domain_name"]

        out.append((cid, name))

    return out


# ---------- CAMPOS OBLIGATORIOS ----------
def get_required_attrs(cat_id: str):
    """
    Devuelve los atributos con tags.required == True para la categoría.
    Cachea la respuesta en .ml_cache/attrs_<cat_id>.json
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

    return [a for a in data if a.get("tags", {}).get("required")]
