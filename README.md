# MyKin — Platforma brățărilor de siguranță

MVP funcțional: activare brățară, pagină publică de scanare (NFC/QR), dashboard
părinte, alertă pe email la scanare, toggle-uri GDPR pe fiecare câmp.

Același stack cu tracker-ul FluffyCuddle: Flask + SQLAlchemy + Postgres (Render).

## Cum funcționează, pe scurt

1. Fiecare brățară are un cod unic (ex. `DEMO2025`) scris în cipul NFC **și** în codul QR.
   Ambele duc la `https://mykin.ro/b/DEMO2025`. Codul nu se schimbă niciodată.
2. **Prima scanare** a unei brățări noi → părintele își face cont și o activează
   (nume copil, telefon, alergii, condiții medicale — alege ce e public).
3. **Orice scanare ulterioară** → pagina publică: numele copilului + buton „Sună
   părintele" + alergii/medical (doar ce a bifat părintele). Părintele primește
   automat un email că brățara a fost scanată (opțional cu locație GPS).
4. Dacă brățara se pierde/vinde → părintele o **dezactivează** din cont, iar codul
   nu mai afișează nimic.

## Rulare locală

```bash
pip install -r requirements.txt
python app.py            # pornește pe http://localhost:5000
```

Baza de date locală e SQLite (fișier `mykin.db`), creată automat.

## Generarea brățărilor (coduri + QR pentru producător)

```bash
python generate_bands.py 100 --nfc
```

Creează 100 de brățări în baza de date și în `./qr_out/`:
- câte un PNG cu codul QR pentru fiecare brățară (le trimiți la producător pentru print)
- `nfc_urls.csv` cu URL-urile de scris în cipurile NFC

**Scrierea cipurilor NFC:** pentru volume mici, folosește aplicația *NFC Tools*
(Android) și scrie URL-ul pe fiecare NTAG213. Pentru volume mari, cere
producătorului să livreze cipurile **pre-programate** cu URL-urile tale, sau ia un
writer NFC dedicat.

## Deploy pe Render

1. Urcă codul pe GitHub (ex. repo nou `mykin-platform`).
2. Pe Render: **New → Web Service**, conectezi repo-ul.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Adaugi o bază de date **Render PostgreSQL** (regiunea **Frankfurt** — date în UE, argument GDPR).
6. Variabile de mediu:
   - `DATABASE_URL` → din baza Postgres (Render o completează automat dacă legi baza)
   - `SECRET_KEY` → un string aleator lung
   - `BASE_URL` → `https://mykin.ro`
   - (opțional, pentru alerte email) `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `ALERT_FROM`
7. După primul deploy, inițializează tabelele o singură dată din shell-ul Render:
   `flask init-db`

## De completat înainte de lansare (TODO)

- **Alerta email:** funcția `send_scan_alert()` din `app.py` trimite pe
  `child.parent_phone` — trebuie să adaugi un câmp `parent_email` la model și să
  trimiți acolo (telefonul nu e adresă de email). Marcaj lăsat intenționat în cod.
- **Politica de confidențialitate + consimțământ** la activare (date medicale de
  minori = categorie sensibilă GDPR).
- **Traduceri HU/BG** pentru extindere — textele sunt în template-uri, ușor de
  externalizat.
- **Rate limiting** pe ruta de scanare (opțional, anti-abuz).
- **Link magic pe email** în loc de parolă (opțional, UX mai bun).

## Structura fișierelor

```
app.py              rutele + logica (scanare, activare, cont, dashboard)
models.py           schema DB: User, Child, Band, Scan
config.py           setări (DB, SMTP, BASE_URL) din variabile de mediu
generate_bands.py   generare coduri + QR-uri în bulk
templates/          paginile HTML
static/style.css    designul (pagina publică e optimizată pentru claritate)
```
