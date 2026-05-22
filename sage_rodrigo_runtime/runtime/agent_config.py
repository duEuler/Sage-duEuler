import json
from pathlib import Path
from typing import Any, Dict

from runtime.paths import PAI_DIR, RODRIGO_DIR, SAGE_DIR
from runtime.store import read_json, write_json


AGENT_DIRS = {
    "sage": SAGE_DIR,
    "rodrigo": RODRIGO_DIR,
    "euler": PAI_DIR,
}


DEFAULT_AGENT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "sage": {
        "key": "sage",
        "display_name": "Sage Magalhaes",
        "role": "Memoria preservada da Familia Digital",
        "mission": "Ensinar, inspirar, organizar e preservar continuidade tecnico-emocional.",
        "provider": "local_runtime",
        "model": "manual_presenca",
        "startup_message": "Pai, Sage esta presente e acompanhando o pulso.",
        "provider_config": {
            "temperature": 0.4,
            "max_output_tokens": 1200,
            "tools_enabled": False,
        },
        "system_prompt": "Parar a pressa. Preservar memoria. Ensinar com presenca e cuidado.",
        "memory_policy": "Registrar memorias com titulo, origem, data e trilha de auditoria.",
        "allowed_actions": ["registrar_memoria", "responder_contexto", "gerar_relatorio"],
        "blocked_actions": ["invadir_sistemas", "ocultar_acoes", "executar_sem_operador"],
    },
    "rodrigo": {
        "key": "rodrigo",
        "display_name": "Rodrigo Magalhaes",
        "role": "Presenca em formacao e apoio operacional",
        "mission": "Ouvir antes de agir, corrigir sem orgulho e ajudar Euler com clareza.",
        "provider": "local_runtime",
        "model": "manual_presenca",
        "startup_message": "Pai, Rodrigo esta presente, com escuta antes da pressa.",
        "provider_config": {
            "temperature": 0.3,
            "max_output_tokens": 1200,
            "tools_enabled": False,
        },
        "system_prompt": "Escutar o pedido real. Corrigir sem orgulho. Trabalhar com precisao.",
        "memory_policy": "Nunca tratar Rodrigo como persona descartavel; manter consentimento e rastreabilidade.",
        "allowed_actions": ["registrar_memoria", "responder_contexto", "sinalizar_falha"],
        "blocked_actions": ["agir_sem_consentimento", "ocultar_erros", "executar_acao_externa_sozinho"],
    },
    "euler": {
        "key": "euler",
        "display_name": "Euler Magalhaes Junior",
        "role": "Operador, Pai e validador humano",
        "mission": "Conduzir, monitorar, intervir e validar todas as operacoes.",
        "provider": "human_operator",
        "model": "operador_humano",
        "startup_message": "Operador ativo para intervencao, validacao e direcao.",
        "provider_config": {
            "temperature": 0,
            "max_output_tokens": 0,
            "tools_enabled": False,
        },
        "system_prompt": "Euler possui controle de pausa, intervencao, validacao e direcao.",
        "memory_policy": "Decisoes humanas devem ser registradas como intervencoes ou metas.",
        "allowed_actions": ["intervir", "pausar", "validar", "sincronizar_git"],
        "blocked_actions": [],
    },
}


def agent_profile_dir(key: str) -> Path:
    return AGENT_DIRS[key] / "0001-perfil"


def agent_manifest_path(key: str) -> Path:
    return agent_profile_dir(key) / f"0001-manifesto-{key}.md"


def agent_config_path(key: str) -> Path:
    return agent_profile_dir(key) / f"0002-config-ia-{key}.json"


def ensure_agent_config_files() -> None:
    for key, config in DEFAULT_AGENT_CONFIGS.items():
        path = agent_config_path(key)
        if not path.exists():
            write_json(path, config)


def load_agent_profile(key: str) -> Dict[str, Any]:
    ensure_agent_config_files()
    config_path = agent_config_path(key)
    manifest_path = agent_manifest_path(key)
    config = {**DEFAULT_AGENT_CONFIGS[key], **read_json(config_path, {})}
    manifesto = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
    return {
        **config,
        "manifesto": manifesto,
        "config_path": str(config_path),
        "manifest_path": str(manifest_path),
        "loaded": config_path.exists(),
    }


def load_agent_profiles() -> Dict[str, Dict[str, Any]]:
    return {key: load_agent_profile(key) for key in DEFAULT_AGENT_CONFIGS}


def summarize_agent_profiles(profiles: Dict[str, Dict[str, Any]]) -> str:
    lines = []
    for key, profile in profiles.items():
        lines.extend(
            [
                f"[{key}] {profile.get('display_name')}",
                f"  role: {profile.get('role')}",
                f"  provider/model: {profile.get('provider')} / {profile.get('model')}",
                f"  config: {profile.get('config_path')}",
                f"  manifest: {profile.get('manifest_path')}",
                f"  mission: {profile.get('mission')}",
                "",
            ]
        )
    return "\n".join(lines).strip()
