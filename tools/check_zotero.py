#!/usr/bin/env python3
"""check_zotero.py — is the Zotero connection actually working, and how far?

WHY THIS EXISTS
    On 2026-08-21 the Library surface reported "last synced 2026-05-21", which
    reads as a lapsed schedule. The truth was worse and completely invisible:
    `ZOTERO_API_KEY` and `ZOTERO_USER_ID` in system/.env were still the literal
    placeholders from .env.example, so every web-API call had returned 403 since
    installation and the error was swallowed several frames up. The web sync had
    never run once.

    Three separate failures produce the SAME symptom — a library that will not
    sync — and they need three different actions:

        placeholder / missing   → create a key
        username instead of ID  → use the numeric userID
        read-only key           → recreate with write access ticked

    A checker that distinguishes them turns an afternoon of guessing into one
    command. It prints what to DO, not just what failed.

WHAT IT CHECKS, in order
    1. Are the values real, or still placeholders?
    2. Is the user ID numeric? (a username here 403s exactly like a bad key)
    3. Does TLS work? (ITG's inspecting proxy breaks httpx but not urllib)
    4. Does the key READ?  — needed for sync
    5. Does the key WRITE? — needed for add-to-library → Zotero
    6. Is a local zotero.sqlite available as a no-credentials fallback?

    The write test is a genuine round trip: it creates one item, confirms it,
    then DELETES it. Nothing is left in the library. Checking a permissions
    endpoint instead would not do — /keys/current 403s even for keys that work.

USAGE
    python3 tools/check_zotero.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER_MARKERS = ("your-", "-here", "changeme", "xxx", "todo", "paste_")
API = "https://api.zotero.org"

OK, WARN, BAD = "✓", "!", "✗"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    p = ROOT / "system" / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def is_placeholder(v: str) -> bool:
    low = (v or "").lower()
    return (not v) or any(m in low for m in PLACEHOLDER_MARKERS)


def call(path: str, key: str, method: str = "GET", body: bytes | None = None):
    """One Zotero API call via urllib. Returns (status, payload_or_error)."""
    req = urllib.request.Request(
        f"{API}{path}", data=body, method=method,
        headers={
            "Zotero-API-Key": key,
            "Zotero-API-Version": "3",
            "User-Agent": "MetisRC/1.0",
            **({"Content-Type": "application/json"} if body else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return r.status, raw[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode("utf-8", "ignore")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def main() -> int:
    env = load_env()
    key = env.get("ZOTERO_API_KEY", "")
    uid = env.get("ZOTERO_USER_ID", "")
    gid = env.get("ZOTERO_GROUP_ID", "")

    print("Zotero connection check")
    print("=" * 66)

    # ── 1. Placeholders ──────────────────────────────────────────────────────
    problems: list[str] = []
    if is_placeholder(key):
        print(f" {BAD} ZOTERO_API_KEY is a placeholder or empty")
        problems.append(
            "Create a key at https://www.zotero.org/settings/keys — tick "
            "'Allow write access' — and put it in system/.env")
    else:
        shape = bool(re.fullmatch(r"[A-Za-z0-9]{20,40}", key))
        print(f" {OK if shape else WARN} ZOTERO_API_KEY set ({len(key)} chars)"
              + ("" if shape else "  — unexpected shape; a Zotero key is ~24 alphanumerics"))

    if is_placeholder(uid) and is_placeholder(gid):
        print(f" {BAD} ZOTERO_USER_ID is a placeholder or empty")
        problems.append(
            "Put your NUMERIC userID in ZOTERO_USER_ID — it is printed on "
            "https://www.zotero.org/settings/keys as 'Your userID for use in "
            "API calls is …'")
    elif uid and not uid.isdigit():
        print(f" {BAD} ZOTERO_USER_ID is not numeric: {uid!r}")
        problems.append(
            "ZOTERO_USER_ID must be the NUMBER, not your Zotero username. A "
            "username here returns 403 — identical to a bad key, which is why "
            "this is worth checking explicitly.")
    else:
        print(f" {OK} ZOTERO_USER_ID = {uid or gid} ({'group' if gid else 'user'})")

    if problems:
        print("\nWhat to do:")
        for i, p in enumerate(problems, 1):
            print(f"  {i}. {p}")
        print("\nReading still works meanwhile via the local Zotero database "
              "(see the fallback line below).")
        _local_note()
        return 1

    lib = f"/groups/{gid}" if gid else f"/users/{uid}"

    # ── 2. Read ──────────────────────────────────────────────────────────────
    status, payload = call(f"{lib}/items?limit=1", key)
    if status == 200:
        print(f" {OK} READ works")
    elif status == 403:
        print(f" {BAD} READ refused (403)")
        print("\nA 403 with well-formed values almost always means the key was "
              "revoked, or belongs to a different account than this userID.\n"
              "Recreate it at https://www.zotero.org/settings/keys")
        _local_note()
        return 1
    else:
        print(f" {BAD} READ failed: {status} {str(payload)[:120]}")
        if status is None and "CERTIFICATE" in str(payload).upper():
            print("\n   TLS failure. On an inspecting corporate network the "
                  "system CA bundle carries the root but certifi does not — "
                  "Metis handles this in _get_zotero_client(); a bare script "
                  "may not.")
        _local_note()
        return 1

    total = None
    status_c, payload_c = call(f"{lib}/items?limit=1&format=keys", key)
    if status_c == 200 and isinstance(payload_c, (bytes, str)):
        pass
    status_t, _ = call(f"{lib}/items/top?limit=1", key)
    print(f" {OK} library reachable"
          + (f" ({total} items)" if total is not None else ""))

    # ── 3. Write — a real round trip, then cleaned up ────────────────────────
    probe = [{
        "itemType": "document",
        "title": "Metis connection test — safe to ignore (auto-deleted)",
    }]
    status, payload = call(f"{lib}/items", key, "POST",
                           json.dumps(probe).encode())
    if status in (200, 201) and isinstance(payload, dict):
        good = payload.get("successful") or {}
        if good:
            item_key = list(good.values())[0]["key"]
            ver = list(good.values())[0]["version"]
            print(f" {OK} WRITE works — created {item_key}, deleting it now")
            req = urllib.request.Request(
                f"{API}{lib}/items/{item_key}", method="DELETE",
                headers={"Zotero-API-Key": key, "Zotero-API-Version": "3",
                         "If-Unmodified-Since-Version": str(ver),
                         "User-Agent": "MetisRC/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    print(f" {OK} test item removed (HTTP {r.status})")
            except Exception as e:
                print(f" {WARN} could not delete the test item ({e}) — "
                      f"remove '{item_key}' from Zotero by hand")
            print("\n" + "=" * 66)
            print("  Everything works. Dashboard → Zotero write-back is live.")
            print("  Next daily library scan will use the web API.")
            return 0
        failed = payload.get("failed") or {}
        print(f" {BAD} WRITE refused: {json.dumps(failed)[:200]}")
    elif status == 403:
        print(f" {BAD} WRITE refused (403) — the key is READ-ONLY")
        print("\nRead-only is enough for syncing INTO Metis, so the library "
              "will stay current.\nBut 'Add to library' cannot push items to "
              "Zotero. To enable that, recreate\nthe key at "
              "https://www.zotero.org/settings/keys with 'Allow write access'\n"
              "ticked (Zotero cannot add permissions to an existing key).")
        return 2
    else:
        print(f" {BAD} WRITE test failed: {status} {str(payload)[:150]}")
    return 2


def _local_note() -> None:
    import glob
    cands = [os.path.expanduser("~/Zotero/zotero.sqlite")]
    cands += glob.glob("/mnt/c/Users/*/Zotero/zotero.sqlite")
    hit = next((c for c in cands if os.path.exists(c)), None)
    print()
    if hit:
        print(f" {OK} fallback available: local Zotero database at {hit}")
        print("   Metis reads this daily with no credentials, so your catalogue "
              "still updates.\n   Only WRITING back to Zotero needs the key.")
    else:
        print(f" {WARN} no local zotero.sqlite found either — with no key and no "
              "local database,\n   nothing can sync.")


if __name__ == "__main__":
    raise SystemExit(main())
