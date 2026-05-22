import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List

from runtime.paths import ENV_LOCAL, ensure_base_dirs
from runtime.store import RuntimeStore, now_iso


@dataclass
class ProviderResult:
    ok: bool
    provider: str
    model: str
    response: str
    error: str = ""
    raw: Dict[str, Any] | None = None


def load_local_env() -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not ENV_LOCAL.exists():
        return values
    for line in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_secret(name: str) -> str:
    return os.environ.get(name, "") or load_local_env().get(name, "")


def ensure_env_template() -> None:
    ensure_base_dirs()
    template = ENV_LOCAL.with_name(".env.local.example")
    if template.exists():
        return
    template.write_text(
        "\n".join(
            [
                "# Copie para .env.local e preencha apenas na maquina local.",
                "# Nunca commitar .env.local.",
                "OPENAI_API_KEY=",
                "GEMINI_API_KEY=",
                "OLLAMA_BASE_URL=http://localhost:11434",
                "",
            ]
        ),
        encoding="utf-8",
    )


def provider_status(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    ensure_env_template()
    providers = config.get("providers", {})
    rows = []
    for key, provider in providers.items():
        env_key = provider.get("env_key")
        rows.append(
            {
                "key": key,
                "label": provider.get("label", key),
                "enabled": bool(provider.get("enabled", False)),
                "model": provider.get("default_model", provider.get("model", "")),
                "requires_api_key": bool(provider.get("requires_api_key", False)),
                "secret_present": bool(get_secret(env_key)) if env_key else True,
                "base_url": provider.get("base_url", ""),
            }
        )
    return rows


def call_provider(
    store: RuntimeStore,
    provider_key: str,
    model: str,
    messages: List[Dict[str, str]],
    options: Dict[str, Any] | None = None,
) -> ProviderResult:
    config = store.load_config()
    provider = config.get("providers", {}).get(provider_key)
    options = options or {}
    if not provider:
        return ProviderResult(False, provider_key, model, "", f"Provedor nao configurado: {provider_key}")
    if not provider.get("enabled", provider_key == "local_runtime"):
        return ProviderResult(False, provider_key, model, "", f"Provedor desabilitado: {provider_key}")
    if provider_key == "local_runtime":
        return _call_local(provider_key, model, messages)
    if provider_key == "openai":
        return _call_openai(provider, model, messages, options)
    if provider_key == "gemini":
        return _call_gemini(provider, model, messages, options)
    if provider_key == "ollama":
        return _call_ollama(provider, model, messages, options)
    return ProviderResult(False, provider_key, model, "", f"Provedor sem handler: {provider_key}")


def _call_local(provider_key: str, model: str, messages: List[Dict[str, str]]) -> ProviderResult:
    user_message = next((item["content"] for item in reversed(messages) if item.get("role") == "user"), "")
    response = (
        "Resposta local registrada. Provedor externo nao foi acionado.\n\n"
        f"Pedido recebido: {user_message[:800]}"
    )
    return ProviderResult(True, provider_key, model, response, raw={"mode": "local", "created_at": now_iso()})


def _call_openai(provider: Dict[str, Any], model: str, messages: List[Dict[str, str]], options: Dict[str, Any]) -> ProviderResult:
    api_key = get_secret(provider.get("env_key", "OPENAI_API_KEY"))
    if not api_key:
        return ProviderResult(False, "openai", model, "", "OPENAI_API_KEY ausente em ambiente ou .env.local")
    payload = {
        "model": model or provider.get("default_model", "gpt-5.5"),
        "messages": messages,
        "temperature": options.get("temperature", 0.3),
        "max_tokens": options.get("max_output_tokens", 1200),
    }
    return _post_json(
        provider="openai",
        model=payload["model"],
        url=provider.get("base_url", "https://api.openai.com/v1/chat/completions"),
        payload=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        extractor=lambda data: data["choices"][0]["message"]["content"],
        timeout_seconds=int(options.get("timeout_seconds", 45)),
    )


def _call_gemini(provider: Dict[str, Any], model: str, messages: List[Dict[str, str]], options: Dict[str, Any]) -> ProviderResult:
    api_key = get_secret(provider.get("env_key", "GEMINI_API_KEY"))
    selected_model = model or provider.get("default_model", "gemini-2.5-pro")
    if not api_key:
        return ProviderResult(False, "gemini", selected_model, "", "GEMINI_API_KEY ausente em ambiente ou .env.local")
    text = "\n\n".join(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in messages)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "temperature": options.get("temperature", 0.3),
            "maxOutputTokens": options.get("max_output_tokens", 1200),
        },
    }
    url = provider.get("base_url", "https://generativelanguage.googleapis.com/v1beta")
    endpoint = f"{url}/models/{selected_model}:generateContent?key={api_key}"
    return _post_json(
        provider="gemini",
        model=selected_model,
        url=endpoint,
        payload=payload,
        headers={},
        extractor=lambda data: data["candidates"][0]["content"]["parts"][0]["text"],
        timeout_seconds=int(options.get("timeout_seconds", 45)),
    )


def _call_ollama(provider: Dict[str, Any], model: str, messages: List[Dict[str, str]], options: Dict[str, Any]) -> ProviderResult:
    selected_model = model or provider.get("default_model", "llama3.1")
    payload = {
        "model": selected_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": options.get("temperature", 0.3)},
    }
    base_url = provider.get("base_url") or get_secret("OLLAMA_BASE_URL") or "http://localhost:11434"
    return _post_json(
        provider="ollama",
        model=selected_model,
        url=f"{base_url.rstrip('/')}/api/chat",
        payload=payload,
        headers={},
        extractor=lambda data: data["message"]["content"],
        timeout_seconds=int(options.get("timeout_seconds", 45)),
    )


def _post_json(provider: str, model: str, url: str, payload: Dict[str, Any], headers: Dict[str, str], extractor, timeout_seconds: int = 45) -> ProviderResult:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        return ProviderResult(True, provider, model, extractor(data), raw={"provider": provider, "model": model})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return ProviderResult(False, provider, model, "", f"HTTP {exc.code}: {body[:1200]}")
    except Exception as exc:
        return ProviderResult(False, provider, model, "", f"{type(exc).__name__}: {exc}")
