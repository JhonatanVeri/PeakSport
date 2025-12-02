import os
from dotenv import load_dotenv

# Cargar variables del archivo .env (solo local)
load_dotenv()

# Entorno
FLASK_ENV = os.getenv("FLASK_ENV", "development")

# Base de datos
POSTGRES_URI = os.getenv("POSTGRES_URI")

# Fallback local si no existe
if not POSTGRES_URI:
    POSTGRES_URI = "sqlite:///peaksport.db"

# Detectar si estamos ejecutando en Render
ON_RENDER = os.getenv("RENDER") == "true"

SQLALCHEMY_CONFIG = {
    'SQLALCHEMY_DATABASE_URI': POSTGRES_URI,
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
}

# ===============================
# 🔐 SSL solo para Render
# ===============================
if ON_RENDER and not POSTGRES_URI.startswith("sqlite"):
    SQLALCHEMY_CONFIG["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "connect_args": {
            "sslmode": "require",   # PRODUCCIÓN
            "connect_timeout": 10
        }
    }
else:
    # LOCAL: sin SSL
    SQLALCHEMY_CONFIG["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "connect_args": {
            "connect_timeout": 10   # LOCAL sin SSL
        }
    }

# Secret key
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")

DEBUG = FLASK_ENV == 'development'

# ===============================
# Correo
# ===============================
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
