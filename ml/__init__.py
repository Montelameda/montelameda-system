# ml/__init__.py
"""Arranque del módulo Mercado Libre: carga .env automático."""
from dotenv import load_dotenv
load_dotenv()     # ahora tus tokens viven en os.environ
