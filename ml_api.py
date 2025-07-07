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

# ... (todo lo demás igual que antes, OMITIDO para ahorrar espacio: sugerir categorías, comisiones, shipping, etc) ...

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
        print(f"Error publicando en ML: {resp.text}")
        raise Exception(f"Error publicando en ML: {resp.text}")
    return resp.json()

def editar_producto_ml(id_ml, datos_producto):
    access_token = get_ml_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        # Solo algunos campos pueden editarse según ML
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
        print(f"Error editando en ML: {resp.text}")
        raise Exception(f"Error editando en ML: {resp.text}")
    return resp.json()
