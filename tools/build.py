"""
AXIOM Browser — build script
=============================
Run from the project root:

    .venv\\Scripts\\python.exe tools\\build.py

What it does
------------
1. Verifies dependencies (PyInstaller, Pillow).
2. Regenerates assets/axiom.ico from assets/axiom.png.
3. Runs PyInstaller with axiom.spec.
4. Prints the final dist/ path.

The output is dist\\Axiom\\ — a self-contained folder with Axiom.exe.
Run tools\\install.py afterwards to install it system-wide.
"""

import io
import subprocess
import sys
from pathlib import Path

# Force UTF-8 output regardless of terminal codepage
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT   = Path(__file__).resolve().parent.parent
VENV   = ROOT / ".venv" / "Scripts"
PYTHON = VENV / "python.exe"
PYI    = VENV / "pyinstaller.exe"
SPEC   = ROOT / "axiom.spec"
PNG    = ROOT / "assets" / "axiom.png"
ICO    = ROOT / "assets" / "axiom.ico"
DIST   = ROOT / "dist" / "Axiom"


def step(msg: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {msg}")
    print(f"{'-' * 60}")


def run(*cmd, cwd=ROOT) -> None:
    result = subprocess.run(list(cmd), cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"\n[ERROR] Command failed: {' '.join(str(c) for c in cmd)}")


def check_deps() -> None:
    step("Checking dependencies")
    missing = []
    if not PYI.exists():
        missing.append("pyinstaller  →  pip install pyinstaller")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("pillow  →  pip install pillow")
    if missing:
        sys.exit("Missing packages:\n  " + "\n  ".join(missing))
    print("  PyInstaller ✓   Pillow ✓")


def make_icon() -> None:
    step("Generating axiom.ico")
    if not PNG.exists():
        sys.exit(f"[ERROR] Icon source not found: {PNG}")
    from PIL import Image
    img = Image.open(PNG).convert("RGBA")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [img.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[0].save(
        ICO, format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"  Written: {ICO.relative_to(ROOT)}")


def build() -> None:
    step("Running PyInstaller")
    run(str(PYI), str(SPEC), "--noconfirm", "--clean")


def report() -> None:
    step("Build complete")
    exe = DIST / "Axiom.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / 1024 / 1024
        print(f"  Axiom.exe  ({size_mb:.1f} MB)")
        total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
        print(f"  Bundle total: {total / 1024 / 1024:.0f} MB  →  {DIST}")
        print()
        print("  Next step:")
        print(f"    {PYTHON} tools\\install.py")
    else:
        sys.exit(f"[ERROR] Expected executable not found: {exe}")


if __name__ == "__main__":
    check_deps()
    make_icon()
    build()
    report()
