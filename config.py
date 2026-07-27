import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Cheia secretă pentru sesiuni. ÎN PRODUCȚIE setează SECRET_KEY în variabilele de mediu Render.
    SECRET_KEY = os.environ.get("SECRET_KEY", "schimba-asta-in-productie")

    # Baza de date. Local: SQLite (fișier). Pe Render: pui DATABASE_URL cu Postgres.
    # Render dă URL-uri care încep cu "postgres://" — SQLAlchemy vrea "postgresql://".
    _db_url = os.environ.get("DATABASE_URL", "sqlite:///mykin.db")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Domeniul public — se folosește când generezi QR-urile și link-urile brățărilor.
    BASE_URL = os.environ.get("BASE_URL", "https://mykin.ro")

    # Setări pentru alerta pe email la scanare (opțional pentru MVP — completezi când vrei).
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASS = os.environ.get("SMTP_PASS", "")
    ALERT_FROM = os.environ.get("ALERT_FROM", "alerta@mykin.ro")
