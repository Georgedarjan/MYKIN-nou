"""
Generează un lot de brățări: coduri unice în baza de date + fișiere QR (PNG)
gata de trimis la producător.

Rulare:
    python generate_bands.py 100        # generează 100 de brățări
    python generate_bands.py 100 --nfc  # + un CSV cu URL-urile pentru scrierea cipurilor NFC

Codurile evită caracterele ambigue (0/O, 1/I/L) ca să nu existe confuzii.
"""
import sys
import os
import csv
import secrets

import qrcode

from app import app
from models import db, Band
from config import Config

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # fără 0,O,1,I,L
CODE_LEN = 8
OUT_DIR = "qr_out"


def make_code():
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))


def main():
    if len(sys.argv) < 2:
        print("Utilizare: python generate_bands.py <numar> [--nfc]")
        sys.exit(1)

    n = int(sys.argv[1])
    write_nfc_csv = "--nfc" in sys.argv

    os.makedirs(OUT_DIR, exist_ok=True)
    base_url = Config.BASE_URL.rstrip("/")

    nfc_rows = []

    with app.app_context():
        created = 0
        while created < n:
            code = make_code()
            if Band.query.filter_by(code=code).first():
                continue  # coliziune rară — reîncearcă
            band = Band(code=code, status="unactivated")
            db.session.add(band)

            url = f"{base_url}/b/{code}"
            img = qrcode.make(url)
            img.save(os.path.join(OUT_DIR, f"{code}.png"))
            nfc_rows.append({"code": code, "url": url})
            created += 1

        db.session.commit()

    if write_nfc_csv:
        with open(os.path.join(OUT_DIR, "nfc_urls.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["code", "url"])
            w.writeheader()
            w.writerows(nfc_rows)

    print(f"Am generat {n} brățări.")
    print(f"QR-uri salvate în ./{OUT_DIR}/")
    if write_nfc_csv:
        print(f"CSV pentru scrierea NFC: ./{OUT_DIR}/nfc_urls.csv")
    print("\nUrmătorul pas: trimite PNG-urile la producător pentru print pe brățări,")
    print("iar URL-urile din CSV le scrii în cipurile NFC (NFC Tools / writer dedicat).")


if __name__ == "__main__":
    main()
