import requests

URL = "https://operacionbarco.onrender.com/notificaciones/emergencia"

try:
    r = requests.get(URL, timeout=15)
    print("Respuesta:", r.text)
except Exception as e:
    print("Error ejecutando alarma:", e)