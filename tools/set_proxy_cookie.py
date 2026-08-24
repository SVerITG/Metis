#!/usr/bin/env python3
"""set_proxy_cookie.py — teach Metis your institutional session, safely.

WHY THIS EXISTS
    ITM authenticates through OpenAthens, a federated SSO. A background process
    cannot complete that login — there is a browser redirect chain and, usually,
    MFA. The only thing that transfers is a SESSION COOKIE from a browser that
    has already signed in.

    Extracting one by hand is fiddly and error-prone: you have to know which
    cookie, on which host, and copy it without mangling it. Worse, the obvious
    way to hand it over — pasting it into a chat or a shell command — puts a live
    credential for your institutional identity into places it should never be
    (scrollback, shell history, a transcript).

    So this reads your browser's own "Copy as cURL" output from a FILE, extracts
    the cookies itself, and writes them to system/.env. It never prints a cookie
    value: only the names and hosts, which is enough to confirm it worked.

WHAT TO DO
    1. In your browser, sign in to any ITM library resource so OpenAthens has a
       live session (lib.itg.be → Databases → any entry).
    2. Open DevTools (F12) → Network tab.
    3. Visit a redirector link, e.g.
         https://go.openathens.net/redirector/itg.be?url=https%3A%2F%2Fwww.sciencedirect.com%2F
    4. In the Network list, right-click the FIRST request → Copy → "Copy as cURL"
       (on Firefox: Copy Value → Copy as cURL).
    5. Paste it into a file, e.g.  ~/oa-curl.txt
    6. Run:   python3 tools/set_proxy_cookie.py ~/oa-curl.txt
    7. Delete the file.       rm ~/oa-curl.txt

SECURITY, PLAINLY
    A session cookie is a bearer credential: anything holding it can act as you
    on those publisher sites for as long as the session lives. It is stored in
    system/.env, which .gitignore already excludes from git. It expires on its
    own — typically hours to a few weeks — and when it does, downloads simply go
    back to the red dot with "session expired", never to a wrong result.

    If you would rather not store one at all, that is a perfectly good choice:
    the "GET VIA INSTITUTION" link already works without it.

USAGE
    python3 tools/set_proxy_cookie.py <file>     # read a Copy-as-cURL blob
    python3 tools/set_proxy_cookie.py --show     # what is configured (names only)
    python3 tools/set_proxy_cookie.py --clear    # remove it
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / "system" / ".env"
VAR = "LIBRARY_PROXY_COOKIE"


def read_env() -> list[str]:
    return ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []


def write_var(value: str) -> None:
    lines = [l for l in read_env() if l.strip() and not l.startswith(f"{VAR}=")]
    if value:
        lines.append(f"{VAR}={value}")
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_curl(blob: str) -> tuple[str, list[str]]:
    """Extract (host, [name=value, ...]) from a browser 'Copy as cURL' string."""
    # The URL: first quoted http(s) token, or the bare one after `curl`.
    host = ""
    m = re.search(r"""["']?(https?://[^\s"']+)["']?""", blob)
    if m:
        host = urlparse(m.group(1)).hostname or ""

    pairs: list[str] = []

    # Chrome/Edge:  -H 'cookie: a=1; b=2'      Firefox: -H "Cookie: a=1; b=2"
    for hm in re.finditer(r"""-H\s+(['"])\s*cookie\s*:\s*(.*?)\1""",
                          blob, re.I | re.S):
        pairs += [p.strip() for p in hm.group(2).split(";") if "=" in p]

    # curl also supports  -b 'a=1; b=2'
    for bm in re.finditer(r"""(?:^|\s)-b\s+(['"])(.*?)\1""", blob, re.S):
        pairs += [p.strip() for p in bm.group(2).split(";") if "=" in p]

    # De-duplicate, keep order.
    seen, out = set(), []
    for p in pairs:
        name = p.split("=", 1)[0].strip()
        if name and name not in seen:
            seen.add(name)
            out.append(p)
    return host, out


def main() -> int:
    args = sys.argv[1:]

    if not args:
        print(__doc__.split("USAGE")[0].split("WHAT TO DO")[1].strip())
        print("\nRun with a file, or --show / --clear.")
        return 1

    if args[0] == "--clear":
        write_var("")
        print(f"✓ {VAR} removed. Downloads fall back to the "
              f"'GET VIA INSTITUTION' link, which needs no session.")
        return 0

    if args[0] == "--show":
        cur = ""
        for l in read_env():
            if l.startswith(f"{VAR}="):
                cur = l.split("=", 1)[1]
        if not cur:
            print(f"{VAR} is not set — the automated institutional download is "
                  f"off; the browser link-out still works.")
            return 0
        for chunk in cur.split(";;"):
            domain, _, pairs = chunk.rpartition("|")
            names = [p.split("=", 1)[0].strip() for p in pairs.split(";") if "=" in p]
            print(f"  {domain.strip() or 'go.openathens.net'}: "
                  f"{len(names)} cookie(s) — {', '.join(names)}")
        print("\n(values are never printed)")
        return 0

    src = Path(args[0]).expanduser()
    if not src.exists():
        print(f"✗ no such file: {src}")
        return 1

    host, pairs = parse_curl(src.read_text(encoding="utf-8", errors="ignore"))
    if not pairs:
        print("✗ no cookies found in that file.\n"
              "  Make sure you used Copy → 'Copy as cURL' on a request made "
              "AFTER signing in.\n"
              "  A request with no Cookie header means the browser had no "
              "session for that host.")
        return 1
    if not host:
        host = "go.openathens.net"
        print(f"! could not read the host from the file; assuming {host}")

    write_var(f"{host}|{'; '.join(pairs)}")
    print(f"✓ stored {len(pairs)} cookie(s) for {host} in system/.env")
    print(f"  names: {', '.join(p.split('=', 1)[0] for p in pairs)}")
    print("\n  Values were not printed and are not in your shell history.")
    print(f"  Now delete the source file:   rm {src}")
    print("  Then check it works:          python3 tools/check_proxy.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
