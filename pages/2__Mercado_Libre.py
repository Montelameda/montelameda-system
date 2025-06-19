# pages/2_🛒_Mercado_Libre.py
import streamlit as st, firebase_admin
from firebase_admin import firestore
from ml.ui import draw_page

if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

prod_id = st.query_params.get("id")
if not prod_id:
    st.error("Falta ?id=producto_id en la URL"); st.stop()

doc = db.collection("productos").document(prod_id).get()
if not doc.exists:
    st.error("Producto no encontrado"); st.stop()

producto = doc.to_dict()
ml_item = draw_page(producto)

if ml_item:
    doc.reference.update({"ml_item_id": ml_item})
    st.success("Firestore actualizado ✔️")
