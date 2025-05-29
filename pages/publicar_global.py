import streamlit as st
from login_app import login, esta_autenticado, obtener_rol

# --- Autenticación ---
if not esta_autenticado():
    login()
    st.stop()

rol = obtener_rol()
if rol != "admin":
    st.error("Solo los administradores pueden publicar masivamente.")
    st.stop()

import subprocess

st.title("⚡ Publicar Masivo FB Marketplace")
st.write("Lee tus datos de Firebase y lanza el bot Selenium automáticamente.")

if st.button("🚀 Publicar en todos"):
    with st.spinner("Arrancando quick_publish.py…"):
        proc = subprocess.Popen(
            ["python", "../quick_publish.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for linea in proc.stdout:
            st.text(linea.strip())
        proc.wait()
        if proc.returncode == 0:
            st.success("🎉 ¡Listo, todo publicado!")
        else:
            st.error("❌ Algo falló, revisa los logs arriba.")

