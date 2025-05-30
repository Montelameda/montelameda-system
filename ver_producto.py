import streamlit as st
from io import BytesIO
import zipfile
import requests

st.title("ZIP Test")

urls = [
    "https://picsum.photos/300/200",  # imagen pública random
    "https://picsum.photos/seed/picsum/300/200"
]

zip_buffer = BytesIO()
with zipfile.ZipFile(zip_buffer, "w") as zip_file:
    for idx, url in enumerate(urls):
        try:
            img_data = requests.get(url, timeout=10).content
            zip_file.writestr(f"imagen_{idx+1}.jpg", img_data)
        except Exception as e:
            st.error(f"Error con {url}: {e}")

st.download_button(
    "Descargar ZIP de prueba",
    data=zip_buffer.getvalue(),
    file_name="imagenes_prueba.zip",
    mime="application/zip"
)
