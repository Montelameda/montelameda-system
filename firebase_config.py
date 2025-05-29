
import firebase_admin
from firebase_admin import credentials, firestore

# Inicializar Firebase solo si no está inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate("montelamedaapp-firebase-adminsdk-fbsvc-9cb2f58a51.json")
    firebase_admin.initialize_app(cred)

# Cliente Firestore global
db = firestore.client()
