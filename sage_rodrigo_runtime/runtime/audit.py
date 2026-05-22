import json
import sys
from pathlib import Path

from runtime.engine import PresenceEngine
from runtime.paths import DB_PATH, DIRECTIVES_MD, EVENTS_JSONL, ROOT_DIR, STATE_JSON
from runtime.reports import health_snapshot, render_markdown_report


REQUIRED_PATHS = [
    DB_PATH,
    DIRECTIVES_MD,
    EVENTS_JSONL,
    STATE_JSON,
    ROOT_DIR / "app.py",
    ROOT_DIR / "web_app.py",
    ROOT_DIR / "runtime" / "ui_desktop.py",
    ROOT_DIR / "runtime" / "web_server.py",
]


def main():
    engine = PresenceEngine()
    readiness = engine.readiness_check()
    provider_active = None
    if readiness["ok"]:
        provider_active = engine.provider_active_check()
        if provider_active["ok"]:
            engine.tick()
        else:
            engine.store.save_state(
                {
                    "mode": "provider_unreachable",
                    "last_tick": None,
                    "last_error": "; ".join(provider_active["issues"]),
                    "readiness": readiness,
                    "provider_active_check": provider_active,
                    "directives_loaded": True,
                }
            )
            engine.store.add_event("runtime", "provider_unreachable", "Auditoria encontrou provedor IA inacessivel", provider_active)
    else:
        engine.store.save_state({"mode": "config_required", "last_tick": None, "last_error": "; ".join(readiness["issues"]), "readiness": readiness, "directives_loaded": True})
        engine.store.add_event("runtime", "config_required", "Auditoria encontrou configuracao minima pendente", readiness)
    report_path = render_markdown_report(engine.store)
    failures = []
    for path in REQUIRED_PATHS:
        if not Path(path).exists():
            failures.append(f"Ausente: {path}")
    snapshot = health_snapshot(engine.store)
    print(json.dumps({"snapshot": snapshot, "readiness": readiness, "provider_active": provider_active, "report": str(report_path), "failures": failures}, ensure_ascii=False, indent=2))
    if failures:
        sys.exit(1)
