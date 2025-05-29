import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Inicializar Firebase solo si no está activo
if not firebase_admin._apps:
    try:
        cred_dict = st.secrets["firebase"]  # Cargado desde secrets.toml en Streamlit Cloud
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except KeyError:
        st.error("❌ No se encontró la clave 'firebase' en secrets. Verifica tu archivo .toml.")
        raise
    except Exception as e:
        st.error(f"❌ Error inesperado al inicializar Firebase: {e}")
        raise

# Cliente Firestore listo para usar
db = firestore.client()
