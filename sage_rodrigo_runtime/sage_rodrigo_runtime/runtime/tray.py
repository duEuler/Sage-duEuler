from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable


try:
    import pystray
    from PIL import Image, ImageDraw
except Exception as exc:  # pragma: no cover - depends on optional desktop packages
    pystray = None
    Image = None
    ImageDraw = None
    TRAY_IMPORT_ERROR = exc
else:
    TRAY_IMPORT_ERROR = None


@dataclass
class TrayActions:
    open_window: Callable[[], None]
    start_runtime: Callable[[], None]
    pause_runtime: Callable[[], None]
    pulse_now: Callable[[], None]
    make_report: Callable[[], None]
    quit_app: Callable[[], None]


class TrayController:
    def __init__(self, actions: TrayActions):
        self.actions = actions
        self.icon = None
        self.thread = None

    def available(self) -> bool:
        return pystray is not None and Image is not None and ImageDraw is not None

    def start(self) -> str:
        if not self.available():
            return f"Tray indisponivel: {TRAY_IMPORT_ERROR}"
        if self.icon:
            return "Tray ja esta ativo."
        menu = pystray.Menu(
            pystray.MenuItem("Abrir painel", lambda: self.actions.open_window(), default=True),
            pystray.MenuItem("Iniciar runtime", lambda: self.actions.start_runtime()),
            pystray.MenuItem("Pausar runtime", lambda: self.actions.pause_runtime()),
            pystray.MenuItem("Pulso agora", lambda: self.actions.pulse_now()),
            pystray.MenuItem("Gerar relatorio", lambda: self.actions.make_report()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", lambda: self.stop_and_quit()),
        )
        self.icon = pystray.Icon("SageRodrigoRuntime", self._image(), "Sage e Rodrigo Runtime", menu)
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()
        return "Tray ativo. Duplo clique abre a janela; clique direito mostra o menu."

    def notify(self, title: str, message: str) -> None:
        if self.icon and hasattr(self.icon, "notify"):
            try:
                self.icon.notify(message, title)
            except Exception:
                return

    def stop(self) -> None:
        if self.icon:
            try:
                self.icon.stop()
            finally:
                self.icon = None

    def stop_and_quit(self) -> None:
        self.stop()
        self.actions.quit_app()

    def _image(self):
        image = Image.new("RGBA", (64, 64), (7, 19, 15, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((6, 6, 58, 58), fill=(20, 126, 104, 255), outline=(218, 255, 216, 255), width=3)
        draw.polygon([(32, 14), (45, 23), (41, 45), (32, 52), (23, 45), (19, 23)], fill=(232, 255, 244, 255))
        draw.line((25, 34, 31, 41, 43, 25), fill=(7, 19, 15, 255), width=4)
        return image
