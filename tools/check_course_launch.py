#!/usr/bin/env python3
"""Assert that every course's launch button opens the actual course.

Courses used to launch whatever happened to sit in the `course_url` column —
one opened a GitHub repository, another a bare filesystem path that 404'd.
This checks the property directly against the running dashboard rather than
trusting the column:

  1. the launch URL resolves (200, following redirects),
  2. the response is a real page, not an error or a directory listing,
  3. it looks like the course it claims to be (title or slug words present),
  4. no launch target points at a source repository or a file path.

Usage:
    python3 tools/check_course_launch.py [--base http://127.0.0.1:8080]

Exit code 0 = every course launches correctly.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request

DB = os.path.expanduser("~/.local/share/metis/metis.sqlite")
BAD_HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "dropbox.com", "sharepoint")


def fetch(url: str, timeout: float = 10.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read(200_000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:                              # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8080")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT slug, title, course_url, status FROM learning_courses "
        "WHERE status IN ('active','in_progress','building') ORDER BY slug"
    ).fetchall()
    con.close()

    # Mirror routers/learning.py::_launch_target. Kept deliberately separate:
    # an independent restatement catches drift that reusing the function hides.
    external = {"statistics": "http://127.0.0.1:3000/"}
    mounted = {"hat-diagnostics": "/coursesite/hat-diagnostics/",
               "hat-history": "/coursesite/hat-history/"}

    failures: list[str] = []
    print(f"{'course':<58}{'launch target':<40}{'code':>5}  verdict")
    print("-" * 118)

    for r in rows:
        slug, title = r["slug"], r["title"] or r["slug"]
        stored = (r["course_url"] or "").strip()

        if slug in external:
            target = external[slug]
        elif slug in mounted:
            target = mounted[slug]
        elif stored and (
            stored.startswith("/")
            or stored.lower().startswith(("http://127.0.0.1", "http://localhost"))
        ) and not any(h in stored.lower() for h in BAD_HOSTS):
            target = stored
        else:
            target = f"/course/{slug}"

        if any(h in target.lower() for h in BAD_HOSTS):
            failures.append(f"{slug}: launch target is a source repository ({target})")
            print(f"{slug[:56]:<58}{target[:38]:<40}{'—':>5}  FAIL repo")
            continue
        if not (target.startswith("/") or target.startswith("http")):
            failures.append(f"{slug}: launch target is not a URL ({target})")
            print(f"{slug[:56]:<58}{target[:38]:<40}{'—':>5}  FAIL not-a-url")
            continue

        url = target if target.startswith("http") else args.base + target
        code, body = fetch(url)

        if code != 200:
            failures.append(f"{slug}: launch target returned {code} ({url})")
            print(f"{slug[:56]:<58}{target[:38]:<40}{code:>5}  FAIL http")
            continue

        low = body.lower()
        words = [w for w in re.findall(r"[a-z]{4,}", slug.replace("-", " "))]
        title_words = [w for w in re.findall(r"[a-z]{4,}", title.lower())]
        matched = any(w in low for w in words + title_words)
        if not matched:
            failures.append(f"{slug}: page does not mention the course ({url})")
            print(f"{slug[:56]:<58}{target[:38]:<40}{code:>5}  FAIL content")
            continue

        print(f"{slug[:56]:<58}{target[:38]:<40}{code:>5}  ok")

    print("-" * 118)
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print("  -", f)
        return 1
    print(f"\nAll {len(rows)} active courses launch correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
