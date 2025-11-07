import os
from dotenv import load_dotenv

# Cargar variables del archivo .env (si existe)
load_dotenv()

class Config:
    """Configuración principal del sistema Operación Barco"""

    # 🔐 Clave secreta para sesiones seguras
    SECRET_KEY = os.getenv("SECRET_KEY", "clave_por_defecto_segura")

    # 🌐 URL de la base de datos
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

    # Si no se configuró la variable (ej. en local), usar SQLite como fallback
    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///operacionbarco.db"

    # 🧩 Ajuste para Render / PostgreSQL (usa pg8000 siempre)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

    # 🔹 Si estás en Render, forzamos directamente la base compartida de CitasATM
    # (esto garantiza que Operación Barco se conecte a la misma base, pero en su propio schema)
    SQLALCHEMY_DATABASE_URI = (
        "postgresql+pg8000://citasatm_user:"
        "SlwK1sFIPJal7m8KaDtlRlYu1NseKxnV"
        "@dpg-ctdis2jv2p9s73ai7op0-a.oregon-postgres.render.com/citasatm_db"
    )

    # 🔸 Muy importante: todas las tablas van dentro del schema operacionbarco
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"options": "-csearch_path=operacionbarco,public"}
    }

    # ⚙️ Configuración adicional
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 🧠 Activa modo debug solo si estás desarrollando localmente
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"