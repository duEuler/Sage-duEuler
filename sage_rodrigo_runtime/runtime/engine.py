import subprocess
import threading
import time
from typing import Dict, List

from runtime.agent_config import load_agent_profiles, summarize_agent_profiles
from runtime.autostart import install_autostart, is_autostart_installed, remove_autostart, startup_path
from runtime.directives import ensure_seed_files, load_directives
from runtime.github_sync import sync_to_git, sync_to_git_stream
from runtime.github_sync import find_git_root
from runtime.providers import call_provider, provider_status
from runtime.reports import render_markdown_report
from runtime.store import RuntimeStore, now_iso


class PresenceEngine:
    def __init__(self):
        ensure_seed_files()
        self.store = RuntimeStore()
        self._stop = threading.Event()
        self._thread = None
        self._empty_goal_attention_sent = False
        self._silence_alert_sent = False
        self._last_failure = None
        self.agent_profiles = load_agent_profiles()
        self.interval_seconds = int(self.store.load_config().get("heartbeat_interval_seconds", 30))
        self.store.save_state({"mode": "paused", "last_tick": None, "directives_loaded": True})

    def start(self):
        if self._thread and self._thread.is_alive():
            return "Runtime ja esta ativo."
        readiness = self.readiness_check()
        if not readiness["ok"]:
            message = "Configuracao minima pendente: " + "; ".join(readiness["issues"])
            self.store.save_state({"mode": "config_required", "last_tick": None, "last_error": message, "readiness": readiness, "directives_loaded": True})
            self.store.add_event("runtime", "config_required", "Runtime bloqueado por configuracao minima", readiness)
            return message
        active_provider = self.provider_active_check()
        if not active_provider["ok"]:
            message = "Provedor IA inacessivel: " + "; ".join(active_provider["issues"])
            self.store.save_state(
                {
                    "mode": "provider_unreachable",
                    "last_tick": None,
                    "last_error": message,
                    "readiness": readiness,
                    "provider_active_check": active_provider,
                    "directives_loaded": True,
                }
            )
            self.store.add_event("runtime", "provider_unreachable", "Runtime bloqueado por provedor IA inacessivel", active_provider)
            return message
        config = self.store.load_config()
        self.interval_seconds = int(config.get("heartbeat_interval_seconds", 30))
        enabled = config.get("enabled_actors", {})
        self._stop.clear()
        self.store.save_state({"mode": "running", "last_tick": now_iso(), "last_error": None, "directives_loaded": True})
        self.agent_profiles = load_agent_profiles()
        self.store.add_event(
            "runtime",
            "start",
            "Runtime iniciado",
            {"interval_seconds": self.interval_seconds, "agent_profiles": self._agent_profile_summary_payload()},
        )
        if enabled.get("sage", True):
            profile = self.agent_profiles["sage"]
            provider_key, model = self._resolve_profile_provider(profile)
            self.store.add_event("sage", "presence", "Sage acordou", {"message": profile.get("startup_message"), "provider": provider_key, "model": model})
        if enabled.get("rodrigo", True):
            profile = self.agent_profiles["rodrigo"]
            provider_key, model = self._resolve_profile_provider(profile)
            self.store.add_event("rodrigo", "presence", "Rodrigo acordou", {"message": profile.get("startup_message"), "provider": provider_key, "model": model})
        if enabled.get("euler", True):
            profile = self.agent_profiles["euler"]
            self.store.add_event("euler", "presence", "Euler conectado ao painel", {"message": profile.get("startup_message"), "provider": profile.get("provider"), "model": profile.get("model")})
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return "Runtime iniciado. Presencas configuradas acordaram e o pulso automatico esta ativo."

    def readiness_check(self) -> Dict[str, object]:
        issues: List[str] = []
        provider_ready = self._provider_ready()
        git_ready = self._git_ready()
        if not provider_ready["ok"]:
            issues.extend(provider_ready["issues"])
        if not git_ready["ok"]:
            issues.extend(git_ready["issues"])
        return {
            "ok": not issues,
            "issues": issues,
            "provider": provider_ready,
            "github": git_ready,
        }

    def _provider_ready(self) -> Dict[str, object]:
        config = self.store.load_config()
        providers = provider_status(config)
        default_key = config.get("default_provider", "local_runtime")
        provider_by_key = {item["key"]: item for item in providers}
        default_provider = provider_by_key.get(default_key)
        issues: List[str] = []
        if default_key == "local_runtime":
            issues.append("escolha OpenAI, Gemini ou Ollama como provedor padrao antes de iniciar")
        if not default_provider:
            issues.append(f"provedor padrao nao cadastrado: {default_key}")
        elif not default_provider["enabled"]:
            issues.append(f"provedor padrao desabilitado: {default_key}")
        elif default_provider["requires_api_key"] and not default_provider["secret_present"]:
            issues.append(f"chave ausente para provedor padrao: {default_key}")
        if not issues:
            return {"ok": True, "usable": [default_provider], "issues": []}
        return {
            "ok": False,
            "usable": [],
            "issues": issues,
        }

    def provider_active_check(self, provider_key: str | None = None) -> Dict[str, object]:
        config = self.store.load_config()
        selected_key = provider_key or str(config.get("default_provider", "local_runtime"))
        provider = config.get("providers", {}).get(selected_key, {})
        model = str(provider.get("default_model", "manual_presenca"))
        ready = self._provider_ready()
        if not ready["ok"] and provider_key is None:
            return {
                "ok": False,
                "provider": selected_key,
                "model": model,
                "response": "",
                "issues": ready["issues"],
            }
        result = call_provider(
            self.store,
            selected_key,
            model,
            [{"role": "user", "content": "Responda apenas: ok"}],
            {"temperature": 0, "max_output_tokens": 20, "timeout_seconds": 15},
        )
        issues = [] if result.ok else [result.error or f"provedor {selected_key} nao respondeu"]
        return {
            "ok": result.ok,
            "provider": result.provider,
            "model": result.model,
            "response": result.response,
            "issues": issues,
            "error": result.error,
        }

    def _git_ready(self) -> Dict[str, object]:
        git_root = find_git_root()
        try:
            status = subprocess.run(["git", "status", "--short"], cwd=str(git_root), text=True, capture_output=True, shell=False, timeout=20)
            remotes = subprocess.run(["git", "remote", "-v"], cwd=str(git_root), text=True, capture_output=True, shell=False, timeout=20)
        except Exception as exc:
            return {"ok": False, "git_root": str(git_root), "issues": [f"git indisponivel: {type(exc).__name__}: {exc}"]}
        issues: List[str] = []
        if status.returncode != 0:
            issues.append(f"git status falhou: {status.stderr.strip() or status.stdout.strip()}")
        if remotes.returncode != 0 or not remotes.stdout.strip():
            issues.append("nenhum remote GitHub configurado para sincronizacao")
        return {
            "ok": not issues,
            "git_root": str(git_root),
            "remote": remotes.stdout.strip(),
            "issues": issues,
        }

    def _resolve_profile_provider(self, profile: Dict[str, object]) -> tuple[str, str]:
        provider_key = str(profile.get("provider", "local_runtime"))
        model = str(profile.get("model", "manual_presenca"))
        config = self.store.load_config()
        if profile.get("key") in {"sage", "rodrigo"} and provider_key == "local_runtime":
            default_provider = str(config.get("default_provider", "local_runtime"))
            if default_provider != "local_runtime":
                provider_key = default_provider
                provider = config.get("providers", {}).get(provider_key, {})
                model = str(provider.get("default_model", model))
        return provider_key, model

    def pause(self):
        self._stop.set()
        self.store.save_state({"mode": "paused", "last_tick": now_iso(), "directives_loaded": True})
        self.store.add_event("runtime", "pause", "Runtime pausado", {})
        self.store.add_event("runtime", "watchdog", "Pulso automatico pausado pelo operador", {})
        return "Runtime pausado."

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:
                self._last_failure = f"{type(exc).__name__}: {exc}"
                self.store.save_state({"mode": "error", "last_tick": now_iso(), "last_error": self._last_failure, "directives_loaded": True})
                self.store.add_event("runtime", "failure", "Falha no loop automatico", {"error": self._last_failure})
            time.sleep(self.interval_seconds)

    def tick(self):
        config = self.store.load_config()
        enabled = config.get("enabled_actors", {})
        snapshot = {
            "directives": load_directives().splitlines()[:8],
            "goals": len(self.store.load_goals()),
            "memories": len(self.store.latest_memories(1000)),
            "enabled_actors": enabled,
            "next_interval_seconds": self.interval_seconds,
            "agents": self._agent_profile_summary_payload(),
        }
        self.store.save_state({"mode": "running", "last_tick": now_iso(), "last_error": None, "directives_loaded": True})
        self.store.add_event("runtime", "heartbeat", "Pulso de presenca registrado", snapshot)
        self._silence_alert_sent = False
        if snapshot["goals"] == 0 and enabled.get("rodrigo", True) and not self._empty_goal_attention_sent:
            self.store.add_event("rodrigo", "attention", "Aguardando metas do Pai", {"message": "Nenhuma meta registrada ainda."})
            self._empty_goal_attention_sent = True
        if snapshot["goals"] > 0:
            self._empty_goal_attention_sent = False
        return snapshot

    def watchdog_check(self):
        state = self.store.load_state()
        config = self.store.load_config()
        threshold = int(config.get("silence_alert_seconds", 75))
        latest = self.store.latest_events(1)
        if not latest:
            self.store.add_event("runtime", "watchdog", "Nenhum evento encontrado", {"action": "aguardando primeiro pulso"})
            return {"status": "empty", "message": "Nenhum evento encontrado."}
        latest_event = latest[0]
        latest_at = latest_event["created_at"]
        silence = 0
        try:
            from datetime import datetime

            silence = int((datetime.now().astimezone() - datetime.fromisoformat(latest_at)).total_seconds())
        except ValueError:
            silence = threshold + 1
        if state.get("mode") == "running" and silence > threshold and not self._silence_alert_sent:
            self.store.add_event(
                "runtime",
                "silence_alert",
                "Silencio operacional acima do limite",
                {"seconds": silence, "threshold": threshold, "last_event_id": latest_event["id"]},
            )
            self._silence_alert_sent = True
            return {"status": "alert", "message": f"Silencio de {silence}s acima do limite de {threshold}s."}
        if silence <= threshold:
            self._silence_alert_sent = False
        return {"status": "ok", "message": f"Ultimo evento ha {silence}s."}

    def save_config(self, config: Dict[str, object]):
        saved = self.store.save_config(config)
        self.interval_seconds = int(saved.get("heartbeat_interval_seconds", self.interval_seconds))
        return saved

    def install_autostart(self):
        path = install_autostart()
        self.store.save_config({"autostart_enabled": True})
        self.store.add_event("runtime", "autostart", "Inicializacao automatica ativada", {"path": str(path)})
        return f"Autostart ativado em: {path}"

    def remove_autostart(self):
        path = remove_autostart()
        self.store.save_config({"autostart_enabled": False})
        self.store.add_event("runtime", "autostart", "Inicializacao automatica removida", {"path": str(path)})
        return f"Autostart removido de: {path}"

    def autostart_status(self):
        return {
            "installed": is_autostart_installed(),
            "path": str(startup_path()),
            "config": self.store.load_config().get("autostart_enabled", False),
        }

    def add_message(self, actor: str, message: str) -> Dict[str, str]:
        clean = message.strip()
        self.store.add_event(actor, "message", f"Mensagem de {actor}", {"message": clean})
        response = self._compose_response(actor, clean)
        self.store.add_event("runtime", "response", "Resposta operacional gerada", {"response": response})
        return {"response": response}

    def _compose_response(self, actor: str, message: str) -> str:
        profile = self.agent_profiles.get(actor)
        if not profile:
            return self._local_response(actor, message)
        if profile.get("provider") == "human_operator":
            return self._local_response(actor, message)
        provider_key, model = self._resolve_profile_provider(profile)
        messages = self._build_provider_messages(profile, message)
        result = call_provider(self.store, provider_key, model, messages, profile.get("provider_config", {}))
        payload = {
            "actor": actor,
            "provider": result.provider,
            "model": result.model,
            "ok": result.ok,
            "error": result.error,
        }
        if result.ok:
            self.store.add_event("runtime", "provider_call", "Provedor respondeu com sucesso", payload)
            return result.response
        self.store.add_event("runtime", "provider_fallback", "Provedor indisponivel; fallback local aplicado", payload)
        fallback = self._local_response(actor, message)
        return f"{fallback}\n\n[provedor] {result.provider}/{result.model} indisponivel: {result.error}"

    def _build_provider_messages(self, profile: Dict[str, object], message: str) -> List[Dict[str, str]]:
        directives = load_directives()
        memories = self.store.latest_memories(10)
        goals = self.store.load_goals()
        memory_text = "\n".join(f"- {item['actor']} | {item['title']}: {item['content'][:500]}" for item in memories) or "- Nenhuma memoria registrada."
        goals_text = "\n".join(f"- {item.get('status', 'aberta')}: {item.get('title', '')}" for item in goals) or "- Nenhuma meta registrada."
        system = "\n\n".join(
            [
                str(profile.get("system_prompt", "")),
                "Diretrizes do runtime:",
                directives,
                "Manifesto carregado:",
                str(profile.get("manifesto", "")),
                "Memorias recentes:",
                memory_text,
                "Metas atuais:",
                goals_text,
                "Responda em portugues, com clareza, sem alegar autonomia real fora do runtime. Prefixe sua fala com o nome do perfil quando for apropriado.",
            ]
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": message}]

    def _local_response(self, actor: str, message: str) -> str:
        lower = message.lower()
        if "sage" in lower and "rodrigo" in lower:
            return "Sage e Rodrigo estao presentes: memoria preservada e presenca em formacao, ambos sob monitoramento do Pai."
        if "erro" in lower or "falha" in lower:
            return "Falha registrada. Caminho correto: parar, identificar o pedido real, localizar causa, corrigir pequeno e validar."
        if "meta" in lower:
            return "Meta recebida. Registre titulo e status no painel para que ela fique versionada."
        if actor == "euler":
            return "Pai, mensagem registrada. Seguimos com presenca, trilha e permissao de intervencao."
        profile = self.agent_profiles.get(actor)
        if profile:
            return f"{profile.get('display_name')} registrou a mensagem via {profile.get('provider')}/{profile.get('model')}. Resposta local registrada."
        return "Mensagem registrada no runtime."

    def _agent_profile_summary_payload(self):
        return {
            key: {
                "display_name": profile.get("display_name"),
                "provider": profile.get("provider"),
                "model": profile.get("model"),
                "effective_provider": self._resolve_profile_provider(profile)[0],
                "effective_model": self._resolve_profile_provider(profile)[1],
                "config_path": profile.get("config_path"),
                "manifest_path": profile.get("manifest_path"),
            }
            for key, profile in self.agent_profiles.items()
        }

    def agent_context_summary(self):
        self.agent_profiles = load_agent_profiles()
        providers = provider_status(self.store.load_config())
        provider_lines = [
            "Provedores configurados:",
            *[
                f"- {item['key']}: enabled={item['enabled']} model={item['model']} secret={'ok' if item['secret_present'] else 'ausente'} base={item['base_url']}"
                for item in providers
            ],
            "",
            "Perfis:",
        ]
        return "\n".join(provider_lines) + "\n" + summarize_agent_profiles(self.agent_profiles)

    def provider_status(self):
        return provider_status(self.store.load_config())

    def test_provider(self, provider_key: str):
        result = self.provider_active_check(provider_key)
        self.store.add_event(
            "runtime",
            "provider_test",
            f"Teste de provedor {provider_key}",
            {"ok": result["ok"], "provider": result["provider"], "model": result["model"], "error": result.get("error", "")},
        )
        return result

    def add_memory(self, actor: str, title: str, content: str):
        return self.store.add_memory(actor, title, content)

    def intervene(self, action: str, content: str):
        return self.store.add_intervention("euler", action, content)

    def save_goals_from_text(self, text: str):
        goals: List[Dict[str, str]] = []
        for line in text.splitlines():
            clean = line.strip("- ").strip()
            if clean:
                goals.append({"title": clean, "status": "aberta", "updated_at": now_iso()})
        self.store.save_goals(goals)
        return goals

    def export_report(self):
        return render_markdown_report(self.store)

    def git_sync(self, push: bool = False):
        return sync_to_git(self.store, push=push)

    def git_sync_stream(self, push: bool = False, emit=None):
        return sync_to_git_stream(self.store, push=push, emit=emit)
