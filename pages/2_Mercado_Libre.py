# pages/2_Mercado_Libre.py
import streamlit as st
import firebase_admin
from firebase_admin import firestore
from ml.ui import draw_page

# Inicializar Firebase solo si no está inicializado
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

# Obtener ID del producto desde la URL (compatibilidad amplia)
prod_id = st.experimental_get_query_params().get("id", [None])[0]
if not prod_id:
    st.error("Falta ?id=producto_id en la URL")
    st.stop()

# Buscar el producto en Firestore
doc = db.collection("productos").document(prod_id).get()
if not doc.exists:
    st.error("Producto no encontrado")
    st.stop()

producto = doc.to_dict()
ml_item = draw_page(producto)

if ml_item:
    doc.reference.update({"ml_item_id": ml_item})
    st.success("Firestore actualizado ✔️")
