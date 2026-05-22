from pathlib import Path
from typing import Dict, List

from runtime.paths import REPORTS_DIR
from runtime.store import RuntimeStore, now_iso


def render_markdown_report(store: RuntimeStore) -> Path:
    events = store.latest_events(30)
    memories = store.latest_memories(20)
    goals = store.load_goals()
    report_path = REPORTS_DIR / f"{now_iso().replace(':', '-')}-relatorio-runtime.md"
    lines: List[str] = [
        "# Relatorio Sage Rodrigo Runtime",
        "",
        f"Gerado em: {now_iso()}",
        "",
        "## Estado",
        "",
        f"```json\n{store.load_state()}\n```",
        "",
        "## Metas",
        "",
    ]
    if goals:
        lines.extend([f"- [{item.get('status', 'aberta')}] {item.get('title', '')}" for item in goals])
    else:
        lines.append("- Nenhuma meta registrada.")
    lines.extend(["", "## Ultimos eventos", ""])
    lines.extend([f"- {item['created_at']} | {item['actor']} | {item['event_type']} | {item['title']}" for item in events])
    lines.extend(["", "## Ultimas memorias", ""])
    lines.extend([f"- {item['created_at']} | {item['actor']} | {item['title']}" for item in memories])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    store.add_event("runtime", "report", "Relatorio exportado", {"path": str(report_path)})
    return report_path


def health_snapshot(store: RuntimeStore) -> Dict[str, object]:
    state = store.load_state()
    return {
        "generated_at": now_iso(),
        "mode": state.get("mode", "unknown"),
        "latest_events": store.count_events(),
        "latest_memories": len(store.latest_memories(10)),
        "goals": len(store.load_goals()),
    }
