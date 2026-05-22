from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
REPORTS_DIR = ROOT_DIR / "reports"
SECRETS_DIR = ROOT_DIR / "secrets"
ENV_LOCAL = ROOT_DIR / ".env.local"

DB_DIR = DATA_DIR / "0000-banco"
SAGE_DIR = DATA_DIR / "0001-sage"
RODRIGO_DIR = DATA_DIR / "0002-rodrigo"
PAI_DIR = DATA_DIR / "0003-pai-euler"
DIRETRIZES_DIR = DATA_DIR / "0004-diretrizes"
OPERACOES_DIR = DATA_DIR / "0005-operacoes"
ESTADO_DIR = DATA_DIR / "0006-estado"

EVENTS_DIR = OPERACOES_DIR / "0001-eventos"
MEMORIES_DIR = OPERACOES_DIR / "0002-memorias"
INTERVENTIONS_DIR = OPERACOES_DIR / "0003-intervencoes"
GOALS_DIR = OPERACOES_DIR / "0004-metas"
SYNC_DIR = OPERACOES_DIR / "0005-sincronizacao"

DB_PATH = DB_DIR / "0001-runtime.sqlite3"
EVENTS_JSONL = EVENTS_DIR / "0001-events.jsonl"
MEMORIES_JSONL = MEMORIES_DIR / "0001-memories.jsonl"
INTERVENTIONS_JSONL = INTERVENTIONS_DIR / "0001-interventions.jsonl"
GOALS_JSON = GOALS_DIR / "0001-goals.json"
STATE_JSON = ESTADO_DIR / "0001-state.json"
CONFIG_JSON = ESTADO_DIR / "0002-config.json"
DIRECTIVES_MD = DIRETRIZES_DIR / "0001-diretrizes-base.md"


def ensure_base_dirs():
    for path in [
        DATA_DIR,
        LOGS_DIR,
        REPORTS_DIR,
        SECRETS_DIR,
        DB_DIR,
        SAGE_DIR / "0001-perfil",
        SAGE_DIR / "0002-memorias",
        RODRIGO_DIR / "0001-perfil",
        RODRIGO_DIR / "0002-memorias",
        PAI_DIR / "0001-perfil",
        DIRETRIZES_DIR,
        EVENTS_DIR,
        MEMORIES_DIR,
        INTERVENTIONS_DIR,
        GOALS_DIR,
        SYNC_DIR,
        ESTADO_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR)).replace("\\", "/")
