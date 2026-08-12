#!/usr/bin/env python3
"""make-localhost-cert.py — a self-signed HTTPS certificate for 127.0.0.1.

WHY (Keystone P5.4)
    An Office add-in's taskpane is loaded over HTTPS inside a webview. A page
    served over HTTPS may not call `http://localhost` — the browser blocks it as
    mixed content, silently, with no error the user could act on. So the Metis
    dashboard has to be reachable over HTTPS for PowerPoint or Excel to talk to it
    at all. That is the whole reason this file exists.

WHAT IT IS NOT
    Not a real certificate and not a security improvement. It is self-signed, and
    the browser will warn the first time. The traffic never leaves the machine —
    this is a formality demanded by the webview, not protection against anything.
    Being clear about that matters: a self-signed cert presented as "now it's
    secure" teaches the user to click through warnings, which is worse than the
    inconvenience it saves.

USAGE
    python3 tools/make-localhost-cert.py          # writes system/config/certs/
    python3 tools/make-localhost-cert.py --force  # regenerate
"""
from __future__ import annotations

import datetime
import ipaddress
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / "system" / "config" / "certs"
CERT = CERT_DIR / "localhost.pem"
KEY = CERT_DIR / "localhost-key.pem"
DAYS = 825          # the maximum most browsers accept for a leaf certificate


def main() -> int:
    force = "--force" in sys.argv
    if CERT.is_file() and KEY.is_file() and not force:
        print(f"Certificate already present:\n  {CERT}\n  {KEY}\nUse --force to regenerate.")
        return 0
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        print("The `cryptography` package is required. It ships with Metis's venv:\n"
              "  ~/.local/share/metis-mcp/.venv/bin/python3 tools/make-localhost-cert.py")
        return 1

    CERT_DIR.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Metis (local only)"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=DAYS))
        # Both the name and the literal IP: an add-in may target either, and a cert
        # missing the IP fails with a name-mismatch that reads like a server fault.
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        ]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    KEY.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    try:
        os.chmod(KEY, 0o600)
    except Exception:
        pass

    print(f"Wrote a self-signed certificate valid for {DAYS} days:\n  {CERT}\n  {KEY}\n")
    print("Start the dashboard over HTTPS with:\n  METIS_HTTPS=1 bash system/app-py/run.sh\n")
    print("Your browser will warn the first time — it is self-signed, and the traffic\n"
          "never leaves this computer. Trust it once and the add-in can connect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
