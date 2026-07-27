from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Părintele / proprietarul contului."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship("Child", backref="owner", cascade="all, delete-orphan")
    bands = db.relationship("Band", backref="owner", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Child(db.Model):
    """Profilul copilului. Părintele alege ce câmpuri sunt publice (GDPR)."""
    __tablename__ = "children"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(120), nullable=False)
    parent_phone = db.Column(db.String(40), nullable=False)
    parent_phone_2 = db.Column(db.String(40))  # contact secundar opțional
    allergies = db.Column(db.Text)
    medical = db.Column(db.Text)
    notes = db.Column(db.Text)  # ex: "Nu vorbește româna", "poartă aparat auditiv"

    # Toggle-uri de vizibilitate publică. Numărul de telefon e mereu vizibil
    # (altfel produsul nu are sens), dar restul le controlează părintele.
    show_name = db.Column(db.Boolean, default=True)
    show_allergies = db.Column(db.Boolean, default=True)
    show_medical = db.Column(db.Boolean, default=True)
    show_notes = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bands = db.relationship("Band", backref="child")


class Band(db.Model):
    """O brățară fizică. Codul e scris în NFC + QR și nu se schimbă niciodată."""
    __tablename__ = "bands"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)

    # unactivated = fabricată dar nerevendicată | active = legată de un copil | disabled = dezactivată de părinte
    status = db.Column(db.String(20), default="unactivated", nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))   # null până la activare
    child_id = db.Column(db.Integer, db.ForeignKey("children.id"))  # null până la activare

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activated_at = db.Column(db.DateTime)

    scans = db.relationship("Scan", backref="band", cascade="all, delete-orphan")


class Scan(db.Model):
    """Jurnalul scanărilor — pentru alerta către părinte + istoric."""
    __tablename__ = "scans"

    id = db.Column(db.Integer, primary_key=True)
    band_id = db.Column(db.Integer, db.ForeignKey("bands.id"), nullable=False)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)   # doar dacă găsitorul acceptă locația în browser
    longitude = db.Column(db.Float)
    user_agent = db.Column(db.String(255))
