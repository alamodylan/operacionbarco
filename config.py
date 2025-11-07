import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave_por_defecto_segura")

    # Obtener la URL base
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///operacionbarco.db"

    # Ajustar formato del URI a SQLAlchemy con pg8000
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

    # 🔹 URI final (tu base en Render)
    SQLALCHEMY_DATABASE_URI = (
        "postgresql+pg8000://citasatm_user:SlwK1sFIPJal7m8KaDtlRlYu1NseKxnV@"
        "dpg-ctdis2jv2p9s73ai7op0-a.oregon-postgres.render.com/citasatm_db"
    )

    # 🔹 Importante: removemos "options" y forzamos schema vía search_path manual
    SQLALCHEMY_ENGINE_OPTIONS = {
        "execution_options": {"schema_translate_map": {"None": "operacionbarco"}}
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Variables de WhatsApp
    WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE")
    CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY")

    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"