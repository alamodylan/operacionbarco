import os
from dotenv import load_dotenv

# Cargar variables del archivo .env (si existe)
load_dotenv()

class Config:
    # Clave de seguridad para sesiones
    SECRET_KEY = os.getenv("SECRET_KEY", "clave_por_defecto_segura")

    # Obtener la URL de base de datos
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # Si no se configuró la variable en Render/local, usar SQLite por defecto
    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///operacionbarco.db"

    # Forzar uso de pg8000 en lugar de psycopg2 o asyncpg
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

    # Configuración de SQLAlchemy
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Modo debug automático si está en desarrollo
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"