import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        cred_dict = dict(st.secrets["firebase"])  # Se copia el dict real
        # 🔥 Arreglamos el formato del private_key (convertimos '\n' en saltos de línea reales)
        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        st.success("✅ Firebase inicializado correctamente")
    except KeyError:
        st.error("❌ Faltan campos en el archivo secrets.toml")
        raise
    except Exception as e:
        st.error(f"❌ Error inesperado al inicializar Firebase: {e}")
        raise

db = firestore.client()
