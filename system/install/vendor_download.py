"""
vendor_download.py — Download all required wheels for offline Metis install.

Run this ONCE on a machine with internet access to produce a `wheels/` folder
that can be bundled with the installer. The installer then uses `pip install
--no-index --find-links wheels/` to install without internet.

Usage:
    python vendor_download.py --output wheels/ --platform win_amd64 --python 3.11

Output:
    wheels/          All .whl files for the target platform
    wheels/index.txt Manifest with package name + hash

Requires: pip >= 23.0, internet access
"""

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

PACKAGES = [
    # Core MCP and API
    "mcp>=1.0",
    "anthropic>=0.40",
    "httpx>=0.27",
    "anyio>=4.0",
    "pydantic>=2.0",
    # Dashboard
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    # Research tools
    "feedparser>=6.0",
    "openai>=1.30",               # embeddings
    "pypdf>=4.0",                 # PaperQA2 pre-validation
    "requests>=2.31",
    "pyzotero>=1.5",
    "python-docx>=1.1",
    # ML / embeddings
    "numpy>=1.26",
    "sqlite-vec>=0.1",
    "scikit-learn>=1.4",          # cosine similarity fallback
    # Scheduling
    "apscheduler>=3.10",
    # Audio transcription (optional — large, skip with --no-audio)
    "faster-whisper>=1.0",
    # Utilities
    "python-dotenv>=1.0",
    "pyyaml>=6.0",
    "tqdm>=4.66",
    "packaging>=24.0",
    # Tray launcher
    "pystray>=0.19",
    "Pillow>=10.0",
]

PACKAGES_NO_AUDIO = [p for p in PACKAGES if "faster-whisper" not in p]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def download(
    output: Path,
    platform: str,
    python_version: str,
    no_audio: bool,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    packages = PACKAGES_NO_AUDIO if no_audio else PACKAGES

    print(f"Downloading {len(packages)} packages → {output}/")
    print(f"  Platform: {platform}  Python: {python_version}\n")

    cmd = [
        sys.executable, "-m", "pip", "download",
        "--dest", str(output),
        "--platform", platform,
        "--python-version", python_version,
        "--only-binary", ":all:",
        "--no-deps",
    ] + packages

    result = subprocess.run(cmd)
    if result.returncode != 0:
        # Some packages may not have binary wheels — retry with source allowed
        print("\nRetrying without --only-binary for packages that failed…")
        cmd2 = [
            sys.executable, "-m", "pip", "download",
            "--dest", str(output),
            "--platform", platform,
            "--python-version", python_version,
        ] + packages
        subprocess.run(cmd2, check=True)

    # Write manifest
    wheels = sorted(output.glob("*.whl")) + sorted(output.glob("*.tar.gz"))
    manifest = output / "index.txt"
    with manifest.open("w") as f:
        for w in wheels:
            f.write(f"{w.name}  sha256:{sha256(w)}\n")

    print(f"\n✓ {len(wheels)} files written to {output}/")
    print(f"  Manifest: {manifest}")
    total_mb = sum(w.stat().st_size for w in wheels) / 1_048_576
    print(f"  Total size: {total_mb:.1f} MB")


def main():
    p = argparse.ArgumentParser(description="Download Metis vendor wheels for offline install")
    p.add_argument("--output", default="wheels", help="Output directory (default: wheels/)")
    p.add_argument("--platform", default="win_amd64", help="Target platform (default: win_amd64)")
    p.add_argument("--python", default="3.11", dest="python_version", help="Python version (default: 3.11)")
    p.add_argument("--no-audio", action="store_true", help="Skip faster-whisper (saves ~300 MB)")
    args = p.parse_args()
    download(Path(args.output), args.platform, args.python_version, args.no_audio)


if __name__ == "__main__":
    main()
