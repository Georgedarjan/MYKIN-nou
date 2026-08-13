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
    gender = db.Column(db.String(10))  # 'boy' / 'girl' (opțional, pt gramatica mesajului)
    parent_phone = db.Column(db.String(40), nullable=False)
    parent_phone_2 = db.Column(db.String(40))  # al doilea contact, opțional
    parent_phone_3 = db.Column(db.String(40))  # al treilea contact, opțional
    # etichete flexibile pentru fiecare număr (Tată/Mamă/Bunic/Tutore/etc.)
    phone_label = db.Column(db.String(30))
    phone_label_2 = db.Column(db.String(30))
    phone_label_3 = db.Column(db.String(30))
    # care număr e principal pentru WhatsApp: 1, 2 sau 3
    primary_phone = db.Column(db.Integer, default=1)
    allergies = db.Column(db.Text)
    medical = db.Column(db.Text)
    notes = db.Column(db.Text)  # ex: "Nu vorbește româna", "poartă aparat auditiv"
    photo_url = db.Column(db.String(500))  # link poză (Cloudinary), opțional

    # Toggle-uri de vizibilitate publică. Numărul de telefon e mereu vizibil
    # (altfel produsul nu are sens), dar restul le controlează părintele.
    show_name = db.Column(db.Boolean, default=True)
    show_allergies = db.Column(db.Boolean, default=True)
    show_medical = db.Column(db.Boolean, default=True)
    show_notes = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bands = db.relationship("Band", backref="child")

    def contacts(self):
        """Întoarce lista contactelor completate: [(eticheta, numar, e_principal), ...].
        Doar numerele completate apar. Eticheta implicită dacă lipsește: 'Contact'."""
        raw = [
            (self.phone_label, self.parent_phone, 1),
            (self.phone_label_2, self.parent_phone_2, 2),
            (self.phone_label_3, self.parent_phone_3, 3),
        ]
        primary = self.primary_phone or 1
        result = []
        for label, phone, idx in raw:
            if phone and phone.strip():
                result.append({
                    "label": (label or "").strip() or "Contact",
                    "phone": phone.strip(),
                    "is_primary": (idx == primary),
                })
        # dacă numărul marcat principal nu e completat, primul devine principal
        if not any(c["is_primary"] for c in result) and result:
            result[0]["is_primary"] = True
        return result

    def primary_contact(self):
        """Contactul principal (pentru WhatsApp)."""
        for c in self.contacts():
            if c["is_primary"]:
                return c
        cs = self.contacts()
        return cs[0] if cs else None


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
