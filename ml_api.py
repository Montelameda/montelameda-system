import requests
import json
import pathlib
import datetime

# --- CONFIG (coloca tus credenciales si necesitas token, pero para predecir categoría NO pide token)
ML_CLIENT_ID = "264097672348150"
ML_CLIENT_SECRET = "oCouItXpao4bYX1GZ0ZTAC16brpqLgkP"
ML_REFRESH_TOKEN = "TG-68530d69b78f1e0001a8d29e-2227856718"

TOKEN_CACHE = pathlib.Path(".ml_token.json")

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
