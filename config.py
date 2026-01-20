import os
from dotenv import load_dotenv
from datetime import timedelta

# Cargar variables del archivo .env
load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave_por_defecto_segura")

    # ============================================================
    # 🗄️ BASE DE DATOS
    # ============================================================

    DATABASE_URL = os.getenv("DATABASE_URL", "")

    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///operacionbarco.db"

    # Ajustar formato del URI a SQLAlchemy con pg8000
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://", "postgresql+pg8000://", 1
        )
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+pg8000://", 1
        )

    # 🔹 URI final (Render)
    SQLALCHEMY_DATABASE_URI = (
        "postgresql+pg8000://citasatm_user:SlwK1sFIPJal7m8KaDtlRlYu1NseKxnV@"
        "dpg-ctdis2jv2p9s73ai7op0-a.oregon-postgres.render.com/citasatm_db"
    )

    # 🔹 Forzar schema
    SQLALCHEMY_ENGINE_OPTIONS = {
        "execution_options": {"schema_translate_map": {"None": "operacionbarco"}}
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ============================================================
    # 🔐 SESIÓN (CLAVE PARA MÓVIL)
    # ============================================================

    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True  # Render usa HTTPS

    # ============================================================
    # 🔁 REMEMBER ME (evita logout al dormir navegador)
    # ============================================================

    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True

    # ============================================================
    # 🔔 WHATSAPP / CALLMEBOT (SIN CAMBIOS)
    # ============================================================

    WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE")
    CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY")

    WHATSAPP_PHONE_1 = os.getenv("WHATSAPP_PHONE_1")
    CALLMEBOT_API_KEY_1 = os.getenv("CALLMEBOT_API_KEY_1")

    WHATSAPP_PHONE_2 = os.getenv("WHATSAPP_PHONE_2")
    CALLMEBOT_API_KEY_2 = os.getenv("CALLMEBOT_API_KEY_2")

    WHATSAPP_PHONE_3 = os.getenv("WHATSAPP_PHONE_3")
    CALLMEBOT_API_KEY_3 = os.getenv("CALLMEBOT_API_KEY_3")

    WHATSAPP_PHONE_4 = os.getenv("WHATSAPP_PHONE_4")
    CALLMEBOT_API_KEY_4 = os.getenv("CALLMEBOT_API_KEY_4")

    WHATSAPP_PHONE_5 = os.getenv("WHATSAPP_PHONE_5")
    CALLMEBOT_API_KEY_5 = os.getenv("CALLMEBOT_API_KEY_5")

    # ============================================================
    # 🐞 DEBUG
    # ============================================================

    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"