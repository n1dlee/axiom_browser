"""
AXIOM Browser — Windows installer
===================================
Run from the project root AFTER tools\\build.py succeeds:

    .venv\\Scripts\\python.exe tools\\install.py

What it does
------------
1. Copies dist\\Axiom\\ → %LOCALAPPDATA%\\Programs\\Axiom\\
2. Creates a Start Menu shortcut  (makes it findable via Windows search)
3. Creates a Desktop shortcut
4. Registers AXIOM in Add / Remove Programs (HKCU — no admin needed)
5. Writes an uninstaller batch file

No administrator rights required — everything goes under HKCU / LOCALAPPDATA.

To uninstall
------------
    .venv\\Scripts\\python.exe tools\\install.py --uninstall
OR  Settings → Apps → AXIOM Browser → Uninstall
OR  run %LOCALAPPDATA%\\Programs\\Axiom\\uninstall.bat
"""

import argparse
import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DIST    = ROOT / "dist" / "Axiom"
APP_ID  = "Axiom.Browser.1"
APP_NAME = "AXIOM Browser"
APP_VER  = "1.0.0"
APP_PUB  = "Axiom Project"

# Installation targets
LOCAL = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
INSTALL_DIR = LOCAL / "Programs" / "Axiom"
START_MENU  = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) \
              / "Microsoft" / "Windows" / "Start Menu" / "Programs"
DESKTOP     = Path.home() / "Desktop"
EXE_PATH    = INSTALL_DIR / "Axiom.exe"

# Registry key (HKCU — no admin required)
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AxiomBrowser"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def step(msg: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {msg}")
    print(f"{'-' * 60}")


def make_shortcut(target: Path, shortcut_path: Path, description: str = "") -> None:
    """Create a Windows .lnk shortcut via PowerShell (no pywin32 needed)."""
    ps = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s  = $ws.CreateShortcut("{shortcut_path}"); '
        f'$s.TargetPath      = "{target}"; '
        f'$s.IconLocation    = "{target}, 0"; '
        f'$s.Description     = "{description}"; '
        f'$s.WorkingDirectory = "{target.parent}"; '
        f'$s.Save()'
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        check=True, capture_output=True,
    )


def register_app() -> None:
    """Write HKCU uninstall registry entry (visible in Add/Remove Programs)."""
    uninstall_cmd = str(INSTALL_DIR / "uninstall.bat")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        winreg.SetValueEx(key, "DisplayName",          0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion",       0, winreg.REG_SZ, APP_VER)
        winreg.SetValueEx(key, "Publisher",            0, winreg.REG_SZ, APP_PUB)
        winreg.SetValueEx(key, "InstallLocation",      0, winreg.REG_SZ, str(INSTALL_DIR))
        winreg.SetValueEx(key, "DisplayIcon",          0, winreg.REG_SZ, str(EXE_PATH))
        winreg.SetValueEx(key, "UninstallString",      0, winreg.REG_SZ, uninstall_cmd)
        winreg.SetValueEx(key, "NoModify",             0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair",             0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "EstimatedSize",        0, winreg.REG_DWORD,
                          sum(f.stat().st_size for f in INSTALL_DIR.rglob("*") if f.is_file()) // 1024)


def write_uninstaller() -> None:
    """Write a simple batch-file uninstaller into the install directory."""
    bat = INSTALL_DIR / "uninstall.bat"
    content = f"""@echo off
echo Uninstalling {APP_NAME}...

rem Remove Start Menu shortcut
del /f /q "{START_MENU}\\{APP_NAME}.lnk" 2>nul

rem Remove Desktop shortcut
del /f /q "{DESKTOP}\\{APP_NAME}.lnk" 2>nul

rem Remove registry entry
reg delete "HKCU\\{UNINSTALL_KEY}" /f 2>nul

rem Remove installation directory (self-deleting)
start "" /b cmd /c "timeout /t 1 /nobreak >nul && rd /s /q \\"{INSTALL_DIR}\\""

echo Done.
"""
    bat.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

def install() -> None:
    if not DIST.exists():
        sys.exit(
            f"[ERROR] Built app not found at {DIST}\n"
            "Run  .venv\\Scripts\\python.exe tools\\build.py  first."
        )

    # 1. Copy files
    step(f"Copying files → {INSTALL_DIR}")
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)
    shutil.copytree(DIST, INSTALL_DIR)
    print(f"  {sum(1 for _ in INSTALL_DIR.rglob('*'))} files copied")

    # 2. Start Menu shortcut
    step("Creating Start Menu shortcut")
    START_MENU.mkdir(parents=True, exist_ok=True)
    lnk_start = START_MENU / f"{APP_NAME}.lnk"
    make_shortcut(EXE_PATH, lnk_start, f"{APP_NAME} — fast, dark, private")
    print(f"  {lnk_start}")

    # 3. Desktop shortcut
    step("Creating Desktop shortcut")
    lnk_desktop = DESKTOP / f"{APP_NAME}.lnk"
    make_shortcut(EXE_PATH, lnk_desktop, APP_NAME)
    print(f"  {lnk_desktop}")

    # 4. Registry
    step("Registering with Windows (Add/Remove Programs)")
    register_app()
    print("  HKCU\\...\\Uninstall\\AxiomBrowser  ✓")

    # 5. Uninstaller
    write_uninstaller()
    print(f"  Uninstaller: {INSTALL_DIR / 'uninstall.bat'}")

    step("Installation complete!")
    print(f"  Installed to : {INSTALL_DIR}")
    print(f"  Launch via   : Windows Search → 'AXIOM'")
    print(f"  Or run       : {EXE_PATH}")
    print()
    print("  To uninstall:")
    print("    Settings → Apps → AXIOM Browser → Uninstall")
    print(f"    — or — {INSTALL_DIR / 'uninstall.bat'}")


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

def uninstall() -> None:
    step("Uninstalling AXIOM Browser")
    errors = []

    for lnk in [
        START_MENU / f"{APP_NAME}.lnk",
        DESKTOP / f"{APP_NAME}.lnk",
    ]:
        try:
            lnk.unlink(missing_ok=True)
            print(f"  Removed: {lnk}")
        except OSError as e:
            errors.append(str(e))

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        print("  Registry entry removed")
    except FileNotFoundError:
        pass
    except OSError as e:
        errors.append(str(e))

    if INSTALL_DIR.exists():
        try:
            shutil.rmtree(INSTALL_DIR)
            print(f"  Removed: {INSTALL_DIR}")
        except OSError as e:
            errors.append(f"Could not remove {INSTALL_DIR}: {e}")
            print(f"  [WARN] Cannot remove dir while running — delete manually: {INSTALL_DIR}")

    if errors:
        print("\nSome errors occurred:")
        for e in errors:
            print(f"  {e}")
    else:
        step("Uninstall complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("This installer is Windows-only.")

    parser = argparse.ArgumentParser(description="AXIOM Browser installer")
    parser.add_argument("--uninstall", action="store_true", help="Remove AXIOM Browser")
    args = parser.parse_args()

    if args.uninstall:
        uninstall()
    else:
        install()
