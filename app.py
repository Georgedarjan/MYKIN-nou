import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for, flash, abort
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

from config import Config
from models import db, User, Child, Band, Scan

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Autentifică-te ca să continui."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# ALERTA PE EMAIL LA SCANARE
# ---------------------------------------------------------------------------
def send_scan_alert(child, scan):
    """Trimite email părintelui când brățara e scanată. Eșuează silențios ca
    să nu blocheze afișarea paginii publice către găsitor."""
    if not app.config["SMTP_HOST"]:
        return  # email neconfigurat încă — sar peste (MVP)

    loc = ""
    if scan.latitude and scan.longitude:
        loc = (f"\n\nLocație aproximativă (dacă găsitorul a permis-o):\n"
               f"https://www.google.com/maps?q={scan.latitude},{scan.longitude}")

    body = (
        f"Brățara MyKin a lui {child.name} tocmai a fost scanată.\n"
        f"Ora: {scan.scanned_at.strftime('%d.%m.%Y %H:%M')}"
        f"{loc}\n\n"
        f"Dacă nu ai fost tu, cineva a găsit copilul și vede datele tale de contact."
    )
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"🔔 Brățara lui {child.name} a fost scanată"
    msg["From"] = app.config["ALERT_FROM"]
    msg["To"] = child.parent_phone  # NOTĂ: aici pui emailul părintelui, vezi comentariul de mai jos

    try:
        with smtplib.SMTP(app.config["SMTP_HOST"], app.config["SMTP_PORT"]) as s:
            s.starttls()
            s.login(app.config["SMTP_USER"], app.config["SMTP_PASS"])
            s.send_message(msg)
    except Exception as e:
        app.logger.warning(f"Alerta email a eșuat: {e}")


# ---------------------------------------------------------------------------
# RUTA CENTRALĂ: SCANAREA BRĂȚĂRII  /b/<code>
# Aici ajunge oricine scanează NFC-ul sau codul QR.
# ---------------------------------------------------------------------------
@app.route("/b/<code>")
def scan(code):
    band = Band.query.filter_by(code=code).first()
    if band is None:
        abort(404)

    # Brățară fabricată dar nerevendicată încă
    if band.status == "unactivated":
        if current_user.is_authenticated:
            # Părintele logat scanează brățara nouă → o poate activa
            return redirect(url_for("activate", code=code))
        return render_template("scan_unactivated.html", code=code)

    # Brățară dezactivată de părinte (pierdută/vândută)
    if band.status == "disabled":
        return render_template("scan_disabled.html")

    # Brățară activă → PAGINA PUBLICĂ pe care o vede găsitorul
    child = band.child

    # Logăm scanarea + trimitem alertă (doar dacă NU e chiar proprietarul care-și testează brățara)
    is_owner = current_user.is_authenticated and current_user.id == band.user_id
    if not is_owner:
        scan_row = Scan(
            band_id=band.id,
            scanned_at=datetime.utcnow(),
            user_agent=request.headers.get("User-Agent", "")[:255],
        )
        # Coordonatele vin din JS (pagina cere permisiunea de locație) prin query params, dacă există
        try:
            if request.args.get("lat") and request.args.get("lng"):
                scan_row.latitude = float(request.args["lat"])
                scan_row.longitude = float(request.args["lng"])
        except (ValueError, TypeError):
            pass
        db.session.add(scan_row)
        db.session.commit()
        send_scan_alert(child, scan_row)

    return render_template("scan_public.html", child=child, is_owner=is_owner)


@app.route("/b/<code>/activate", methods=["GET", "POST"])
@login_required
def activate(code):
    band = Band.query.filter_by(code=code).first()
    if band is None:
        abort(404)
    if band.status != "unactivated":
        flash("Această brățară este deja activată.")
        return redirect(url_for("dashboard"))

    children = current_user.children

    if request.method == "POST":
        child_id = request.form.get("child_id")
        if child_id == "new" or not children:
            # Creează un copil nou din datele formularului
            child = Child(
                user_id=current_user.id,
                name=request.form["name"].strip(),
                parent_phone=request.form["parent_phone"].strip(),
                parent_phone_2=request.form.get("parent_phone_2", "").strip() or None,
                allergies=request.form.get("allergies", "").strip() or None,
                medical=request.form.get("medical", "").strip() or None,
                notes=request.form.get("notes", "").strip() or None,
            )
            db.session.add(child)
            db.session.flush()  # ca să avem child.id
        else:
            child = db.session.get(Child, int(child_id))
            if not child or child.user_id != current_user.id:
                abort(403)

        band.status = "active"
        band.user_id = current_user.id
        band.child_id = child.id
        band.activated_at = datetime.utcnow()
        db.session.commit()
        flash(f"Brățara a fost activată pentru {child.name}. E gata de purtat.")
        return redirect(url_for("dashboard"))

    return render_template("scan_activate.html", code=code, children=children)


# ---------------------------------------------------------------------------
# CONT: register / login / logout
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Există deja un cont cu acest email.")
            return redirect(url_for("register"))
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        # dacă venea dintr-o scanare de activare, îl trimitem înapoi acolo
        nxt = request.args.get("next")
        return redirect(nxt or url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(request.form["password"]):
            login_user(user)
            nxt = request.args.get("next")
            return redirect(nxt or url_for("dashboard"))
        flash("Email sau parolă greșită.")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# DASHBOARD PĂRINTE
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    children = current_user.children
    bands = current_user.bands
    return render_template("dashboard.html", children=children, bands=bands)


@app.route("/child/<int:child_id>/edit", methods=["GET", "POST"])
@login_required
def edit_child(child_id):
    child = db.session.get(Child, child_id)
    if not child or child.user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        child.name = request.form["name"].strip()
        child.parent_phone = request.form["parent_phone"].strip()
        child.parent_phone_2 = request.form.get("parent_phone_2", "").strip() or None
        child.allergies = request.form.get("allergies", "").strip() or None
        child.medical = request.form.get("medical", "").strip() or None
        child.notes = request.form.get("notes", "").strip() or None
        child.show_name = "show_name" in request.form
        child.show_allergies = "show_allergies" in request.form
        child.show_medical = "show_medical" in request.form
        child.show_notes = "show_notes" in request.form
        db.session.commit()
        flash("Datele au fost salvate.")
        return redirect(url_for("dashboard"))

    return render_template("child_form.html", child=child)


@app.route("/band/<int:band_id>/disable", methods=["POST"])
@login_required
def disable_band(band_id):
    band = db.session.get(Band, band_id)
    if not band or band.user_id != current_user.id:
        abort(403)
    band.status = "disabled"
    db.session.commit()
    flash("Brățara a fost dezactivată. Codul nu mai afișează date.")
    return redirect(url_for("dashboard"))


@app.route("/band/<int:band_id>/enable", methods=["POST"])
@login_required
def enable_band(band_id):
    band = db.session.get(Band, band_id)
    if not band or band.user_id != current_user.id:
        abort(403)
    if band.child_id:
        band.status = "active"
        db.session.commit()
        flash("Brățara a fost reactivată.")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Pagină de start simplă
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.cli.command("init-db")
def init_db():
    """Creează tabelele. Rulează: flask init-db"""
    db.create_all()
    print("Baza de date a fost inițializată.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
