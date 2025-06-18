import requests, json, pathlib, datetime, urllib.parse

CACHE_TTL_HRS = 24
CACHE_DIR = pathlib.Path(".ml_cache"); CACHE_DIR.mkdir(exist_ok=True)

def _cached(fp):
    if not fp.exists(): return None
    age = (datetime.datetime.now() - datetime.datetime.fromtimestamp(fp.stat().st_mtime)).total_seconds()
    if age > CACHE_TTL_HRS * 3600: return None
    return json.loads(fp.read_text())

# ----------  AUTOCOMPLETAR CATEGORÍAS ----------
def suggest_categories(title: str, site: str = "MLC", limit: int = 5):
    """Devuelve lista [(cat_id, display_name)] ordenada por relevancia."""
    if not title.strip(): return []
    q = urllib.parse.quote(title.strip())
    url = f"https://api.mercadolibre.com/sites/{site}/domain_discovery/search?limit={limit}&q={q}"
    data = requests.get(url, timeout=10).json()
    out = []
    for item in data:
        cid = item["category_id"]
        # Intentamos sacar path completo para que el usuario lo entienda
        cache = _cached(CACHE_DIR / f"path_{cid}.json")
        if not cache:
            path = requests.get(f"https://api.mercadolibre.com/categories/{cid}", timeout=10).json()["path_from_root"]
            CACHE_DIR.joinpath(f"path_{cid}.json").write_text(json.dumps(path, ensure_ascii=False))
        else:
            path = cache
        name = " › ".join(n["name"] for n in path)
        out.append((cid, name))
    return out

# ----------  CAMPOS OBLIGATORIOS ----------
def get_required_attrs(cat_id: str):
    if not cat_id: return []
    fp = CACHE_DIR / f"attrs_{cat_id}.json"
    data = _cached(fp)
    if not data:
        url = f"https://api.mercadolibre.com/categories/{cat_id}/attributes"
        data = requests.get(url, timeout=10).json()
        fp.write_text(json.dumps(data, ensure_ascii=False))
    return [a for a in data if a.get("tags", {}).get("required")]
