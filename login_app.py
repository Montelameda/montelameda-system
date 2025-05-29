import streamlit as st
from firebase_config import db

def login():
    st.title("🔐 Iniciar sesión en MonteLameda System")

    usuario = st.text_input("👤 Usuario", key="usuario_input")
    clave = st.text_input("🔑 Clave", type="password", key="clave_input")

    if st.button("Entrar"):
        if not usuario or not clave:
            st.warning("Por favor completa ambos campos.")
        else:
            doc_ref = db.collection("usuarios").document(usuario)
            doc = doc_ref.get()
            if doc.exists:
                datos = doc.to_dict()
                if datos["clave"] == clave:
                    st.session_state["usuario"] = usuario
                    st.session_state["rol"] = datos["rol"]
                    st.success(f"¡Bienvenido {usuario}!")
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta.")
            else:
                st.error("❌ Usuario no encontrado.")

def esta_autenticado():
    return "usuario" in st.session_state and st.session_state["usuario"]

def obtener_rol():
    return st.session_state.get("rol", "")
