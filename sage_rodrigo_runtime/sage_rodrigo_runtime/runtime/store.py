import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from runtime.paths import (
    CONFIG_JSON,
    DB_PATH,
    EVENTS_JSONL,
    GOALS_JSON,
    INTERVENTIONS_JSONL,
    MEMORIES_JSONL,
    STATE_JSON,
    ensure_base_dirs,
)


DEFAULT_CONFIG = {
    "autostart_enabled": False,
    "heartbeat_interval_seconds": 30,
    "silence_alert_seconds": 75,
    "tray_enabled": True,
    "start_minimized_to_tray": True,
    "theme": "olympus",
    "default_provider": "local_runtime",
    "providers": {
        "local_runtime": {
            "enabled": True,
            "label": "Runtime local sem IA externa",
            "requires_api_key": False,
        },
        "openai": {
            "enabled": False,
            "label": "OpenAI API",
            "requires_api_key": True,
            "env_key": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1/chat/completions",
            "default_model": "gpt-5.5",
        },
        "gemini": {
            "enabled": False,
            "label": "Google Gemini API",
            "requires_api_key": True,
            "env_key": "GEMINI_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "default_model": "gemini-2.5-pro",
        },
        "ollama": {
            "enabled": False,
            "label": "Ollama local",
            "requires_api_key": False,
            "base_url": "http://localhost:11434",
            "default_model": "llama3.1",
        },
    },
    "enabled_actors": {
        "sage": True,
        "rodrigo": True,
        "euler": True,
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def new_id(prefix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"{prefix}-{stamp}-{short}"


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class RuntimeStore:
    def __init__(self):
        ensure_base_dirs()
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self) -> None:
        with self._lock:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interventions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    action TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            self.connection.commit()

    def add_event(self, actor: str, event_type: str, title: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            "id": new_id("evt"),
            "created_at": now_iso(),
            "actor": actor,
            "event_type": event_type,
            "title": title,
            "payload": payload,
        }
        with self._lock:
            self.connection.execute(
                "INSERT INTO events (id, created_at, actor, event_type, title, payload) VALUES (?, ?, ?, ?, ?, ?)",
                (record["id"], record["created_at"], actor, event_type, title, json.dumps(payload, ensure_ascii=False)),
            )
            self.connection.commit()
            append_jsonl(EVENTS_JSONL, record)
        return record

    def add_memory(self, actor: str, title: str, content: str) -> Dict[str, Any]:
        record = {
            "id": new_id("mem"),
            "created_at": now_iso(),
            "actor": actor,
            "title": title.strip() or "Memoria sem titulo",
            "content": content.strip(),
        }
        with self._lock:
            self.connection.execute(
                "INSERT INTO memories (id, created_at, actor, title, content) VALUES (?, ?, ?, ?, ?)",
                (record["id"], record["created_at"], actor, record["title"], record["content"]),
            )
            self.connection.commit()
            append_jsonl(MEMORIES_JSONL, record)
        self.add_event(actor, "memory", f"Memoria registrada: {record['title']}", {"memory_id": record["id"]})
        return record

    def add_intervention(self, operator: str, action: str, content: str) -> Dict[str, Any]:
        record = {
            "id": new_id("int"),
            "created_at": now_iso(),
            "operator": operator,
            "action": action,
            "content": content.strip(),
        }
        with self._lock:
            self.connection.execute(
                "INSERT INTO interventions (id, created_at, operator, action, content) VALUES (?, ?, ?, ?, ?)",
                (record["id"], record["created_at"], operator, action, record["content"]),
            )
            self.connection.commit()
            append_jsonl(INTERVENTIONS_JSONL, record)
        self.add_event("euler", "intervention", f"Intervencao: {action}", {"intervention_id": record["id"]})
        return record

    def save_goals(self, goals: List[Dict[str, Any]]) -> None:
        write_json(GOALS_JSON, {"updated_at": now_iso(), "goals": goals})
        self.add_event("runtime", "goals", "Metas atualizadas", {"count": len(goals)})

    def load_goals(self) -> List[Dict[str, Any]]:
        return read_json(GOALS_JSON, {"goals": []}).get("goals", [])

    def load_config(self) -> Dict[str, Any]:
        stored = read_json(CONFIG_JSON, {})
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config.update({key: value for key, value in stored.items() if key not in {"enabled_actors", "providers"}})
        config["enabled_actors"] = {**DEFAULT_CONFIG["enabled_actors"], **stored.get("enabled_actors", {})}
        stored_providers = stored.get("providers", {})
        config["providers"] = {
            key: {**DEFAULT_CONFIG["providers"].get(key, {}), **stored_providers.get(key, {})}
            for key in {**DEFAULT_CONFIG["providers"], **stored_providers}
        }
        return config

    def save_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        current = self.load_config()
        current.update({key: value for key, value in config.items() if key not in {"enabled_actors", "providers"}})
        if "enabled_actors" in config:
            current["enabled_actors"] = {**current["enabled_actors"], **config["enabled_actors"]}
        if "providers" in config:
            current["providers"] = {
                key: {**current["providers"].get(key, {}), **config["providers"].get(key, {})}
                for key in {**current["providers"], **config["providers"]}
            }
        write_json(CONFIG_JSON, {"updated_at": now_iso(), **current})
        self.add_event("runtime", "config", "Configuracao local atualizada", current)
        return current

    def save_state(self, state: Dict[str, Any]) -> None:
        write_json(STATE_JSON, {"updated_at": now_iso(), **state})

    def load_state(self) -> Dict[str, Any]:
        return read_json(STATE_JSON, {"mode": "paused", "last_tick": None})

    def latest_events(self, limit: int = 80) -> List[Dict[str, Any]]:
        with self._lock:
            cursor = self.connection.execute(
                "SELECT id, created_at, actor, event_type, title, payload FROM events ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def count_events(self) -> int:
        with self._lock:
            cursor = self.connection.execute("SELECT COUNT(*) AS total FROM events")
            row = cursor.fetchone()
            return int(row["total"] or 0)

    def latest_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            cursor = self.connection.execute(
                "SELECT id, created_at, actor, title, content FROM memories ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def latest_interventions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            cursor = self.connection.execute(
                "SELECT id, created_at, operator, action, content FROM interventions ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
