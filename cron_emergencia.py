# cron_emergencia.py
import requests

URL = "https://operacionbarco.onrender.com/notificaciones/emergencia"

def main():
    try:
        print("Ejecutando cron de emergencia...")
        r = requests.get(URL, timeout=20)
        print("Status:", r.status_code)
        print("Response:", r.text[:300])
    except Exception as e:
        print("ERROR ejecutando cron:", e)

if __name__ == "__main__":
    main()