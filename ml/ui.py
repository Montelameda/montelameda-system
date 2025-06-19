# ml/ui.py
import json, streamlit as st
from ml.api import publish_item, validate_item
from ml.helpers import attrs_dict_to_array

def draw_page(prod: dict | None = None) -> str | None:
    st.subheader("🛒 Publicar en Mercado Libre")

    titulo = st.text_input("Título", value=(prod or {}).get("nombre_producto", ""), max_chars=60)
    precio = st.number_input("Precio CLP", value=float((prod or {}).get("precio_mercado_libre", 0)), step=100.0)
    stock  = st.number_input("Stock", 1, 1000, value=int((prod or {}).get("stock", 1)))
    cat_id = st.text_input("Categoría ML", value=(prod or {}).get("ml_cat_id", ""))
    desc   = st.text_area("Descripción", value=(prod or {}).get("descripcion", ""))

    st.divider()
    st.markdown("#### Atributos ML (pega JSON mientras automatizamos)")
    raw = st.text_area("Ej: {\"BRAND\": {\"value_id\": \"123\", \"value_name\": \"Sony\"}}")

    try:
        attrs_dict = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        st.error("JSON inválido"); attrs_dict = {}

    payload = {
        "title": titulo,
        "category_id": cat_id,
        "price": precio,
        "currency_id": "CLP",
        "available_quantity": stock,
        "buying_mode": "buy_it_now",
        "listing_type_id": "gold_special",
        "condition": "new",
        "description": {"plain_text": desc},
        "attributes": attrs_dict_to_array(attrs_dict),
    }

    col1, col2 = st.columns(2)
    ml_id = None

    with col1:
        if st.button("🔍 Validar"):
            with st.spinner("Consultando ML…"):
                try:
                    validate_item(payload)
                    st.success("✅ Sin errores")
                except Exception as e:
                    st.error(f"❌ {e}")

    with col2:
        if st.button("🚀 Publicar"):
            with st.spinner("Publicando…"):
                try:
                    ml_id = publish_item(payload)
                    st.success(f"🎉 Publicado como {ml_id}")
                except Exception as e:
                    st.error(f"❌ {e}")

    return ml_id
