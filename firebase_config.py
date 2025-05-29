import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        # Se asume que estás usando st.secrets en Streamlit Cloud
        cred_dict = st.secrets["firebase"]
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Error inicializando Firebase: {e}")
        raise e

# Cliente de Firestore
db = firestore.client()
