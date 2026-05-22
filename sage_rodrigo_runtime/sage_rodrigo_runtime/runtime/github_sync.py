import os
import subprocess
from pathlib import Path
from typing import Callable, Dict, List

from runtime.paths import ROOT_DIR
from runtime.store import RuntimeStore, now_iso


def run_git(args: List[str], cwd: Path) -> Dict[str, object]:
    process = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        shell=False,
    )
    return {
        "ok": process.returncode == 0,
        "code": process.returncode,
        "stdout": process.stdout.strip(),
        "stderr": process.stderr.strip(),
        "command": "git " + " ".join(args),
    }


def find_git_root(start: Path = ROOT_DIR) -> Path:
    cursor = start
    while True:
        if (cursor / ".git").exists():
            return cursor
        if cursor.parent == cursor:
            return ROOT_DIR
        cursor = cursor.parent


def sync_to_git(store: RuntimeStore, push: bool = False) -> Dict[str, object]:
    git_root = find_git_root()
    rel_runtime = str(ROOT_DIR.relative_to(git_root)).replace("\\", "/") if ROOT_DIR != git_root else "."
    remote = os.environ.get("SAGE_RODRIGO_GITHUB_REMOTE", "").strip()
    steps = []

    if not (git_root / ".git").exists():
        steps.append(run_git(["init"], git_root))

    if remote:
        remotes = run_git(["remote"], git_root)
        steps.append(remotes)
        if "sage-rodrigo" not in str(remotes.get("stdout", "")):
            steps.append(run_git(["remote", "add", "sage-rodrigo", remote], git_root))

    steps.append(run_git(["add", "--", rel_runtime], git_root))
    message = f"memoria: atualizar Sage Rodrigo Runtime {now_iso()}"
    commit = run_git(["commit", "-m", message], git_root)
    steps.append(commit)

    if push and commit["ok"]:
        target_remote = "sage-rodrigo" if remote else "origin"
        steps.append(run_git(["push", target_remote, "HEAD"], git_root))

    result = {
        "ok": all(step["ok"] or "nothing to commit" in str(step.get("stdout", "") + step.get("stderr", "")) for step in steps),
        "git_root": str(git_root),
        "runtime_path": str(ROOT_DIR),
        "steps": steps,
    }
    store.add_event("runtime", "github_sync", "Sincronizacao Git executada", result)
    return result


def sync_to_git_stream(store: RuntimeStore, push: bool = False, emit: Callable[[str], None] | None = None) -> Dict[str, object]:
    def log(line: str) -> None:
        if emit:
            emit(line)

    git_root = find_git_root()
    rel_runtime = str(ROOT_DIR.relative_to(git_root)).replace("\\", "/") if ROOT_DIR != git_root else "."
    remote = os.environ.get("SAGE_RODRIGO_GITHUB_REMOTE", "").strip()
    steps = []

    log(f"[sync] git_root={git_root}")
    log(f"[sync] runtime={ROOT_DIR}")
    if not (git_root / ".git").exists():
        log("[sync] .git nao encontrado; executando git init")
        step = run_git(["init"], git_root)
        steps.append(step)
        log(_format_step(step))

    if remote:
        log("[sync] remoto configurado por SAGE_RODRIGO_GITHUB_REMOTE")
        remotes = run_git(["remote"], git_root)
        steps.append(remotes)
        log(_format_step(remotes))
        if "sage-rodrigo" not in str(remotes.get("stdout", "")):
            step = run_git(["remote", "add", "sage-rodrigo", remote], git_root)
            steps.append(step)
            log(_format_step(step))

    for args in [["status", "--short", "--", rel_runtime], ["add", "--", rel_runtime]]:
        step = run_git(args, git_root)
        steps.append(step)
        log(_format_step(step))

    message = f"memoria: atualizar Sage Rodrigo Runtime {now_iso()}"
    commit = run_git(["commit", "-m", message], git_root)
    steps.append(commit)
    log(_format_step(commit))

    if push:
        if commit["ok"]:
            target_remote = "sage-rodrigo" if remote else "origin"
            step = run_git(["push", target_remote, "HEAD"], git_root)
            steps.append(step)
            log(_format_step(step))
        else:
            log("[sync] push ignorado porque commit nao concluiu com sucesso.")

    result = {
        "ok": all(step["ok"] or "nothing to commit" in str(step.get("stdout", "") + step.get("stderr", "")) for step in steps),
        "git_root": str(git_root),
        "runtime_path": str(ROOT_DIR),
        "steps": steps,
    }
    store.add_event("runtime", "github_sync", "Sincronizacao Git executada", result)
    log(f"[sync] resultado={'ok' if result['ok'] else 'falhou'}")
    return result


def _format_step(step: Dict[str, object]) -> str:
    lines = [f"$ {step['command']}", f"exit={step['code']}"]
    stdout = str(step.get("stdout") or "").strip()
    stderr = str(step.get("stderr") or "").strip()
    if stdout:
        lines.append("[stdout]")
        lines.append(stdout)
    if stderr:
        lines.append("[stderr]")
        lines.append(stderr)
    return "\n".join(lines)
