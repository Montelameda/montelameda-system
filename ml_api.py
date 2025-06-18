import requests, json, pathlib, datetime, os

CACHE_DIR = pathlib.Path(os.getenv("ML_CACHE_DIR", ".ml_cache"))
CACHE_DIR.mkdir(exist_ok=True, parents=True)
CACHE_TTL_SECONDS = int(os.getenv("ML_CACHE_TTL", 24*3600))

def _read_cache(fname):
    fpath = CACHE_DIR / fname
    if not fpath.exists():
        return None
    age = datetime.datetime.now().timestamp() - fpath.stat().st_mtime
    if age > CACHE_TTL_SECONDS:
        return None
    try:
        return json.loads(fpath.read_text(encoding="utf-8"))
    except Exception:
        return None

def _write_cache(fname, data):
    (CACHE_DIR / fname).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def predict_category(title: str, site="MLC"):
    """Devuelve el category_id más probable según el título"""
    if not title:
        return ""
    url = f"https://api.mercadolibre.com/sites/{site}/domain_discovery/search"
    params = {"limit": 1, "q": title}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data:
        return ""
    return data[0].get("category_id", "")

def get_required_attrs(cat_id: str):
    """Retorna lista de atributos obligatorios para una categoría"""
    if not cat_id:
        return []
    cache_fname = f"{cat_id}.json"
    cached = _read_cache(cache_fname)
    if cached is not None:
        attrs = cached
    else:
        url = f"https://api.mercadolibre.com/categories/{cat_id}/attributes"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        attrs = r.json()
        _write_cache(cache_fname, attrs)
    return [a for a in attrs if a.get("tags", {}).get("required") is True]