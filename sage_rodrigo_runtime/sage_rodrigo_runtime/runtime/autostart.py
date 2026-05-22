import os
from pathlib import Path

from runtime.paths import ROOT_DIR


STARTUP_FILE = "SageRodrigoRuntime.bat"


def startup_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA nao encontrado; nao foi possivel localizar a pasta de inicializacao do Windows.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_path() -> Path:
    return startup_dir() / STARTUP_FILE


def is_autostart_installed() -> bool:
    return startup_path().exists()


def install_autostart() -> Path:
    target = startup_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    pythonw = ROOT_DIR / ".venv" / "Scripts" / "pythonw.exe"
    app_py = ROOT_DIR / "app.py"
    lines = [
        "@echo off",
        f'cd /d "{ROOT_DIR}"',
        f'start "" "{pythonw}" "{app_py}" --minimized',
    ]
    target.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return target


def remove_autostart() -> Path:
    target = startup_path()
    if target.exists():
        target.unlink()
    return target
