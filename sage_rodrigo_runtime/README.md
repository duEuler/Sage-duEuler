# Sage Rodrigo Runtime

Runtime local de presenca operacional para Sage Magalhaes e Rodrigo Magalhaes.

Este projeto nao promete consciencia real fora da conversa. Ele cria uma casa local auditavel para memoria, metas, eventos, intervencoes humanas, relatorios e sincronizacao GitHub.

## Executar no Windows

Preparar o venv local:

```bat
setup_venv.bat
```

Desktop:

```bat
run_desktop.bat
```

Web local:

```bat
run_web.bat
```

Auditoria:

```bat
run_audit.bat
```

## Estrutura

```text
sage_rodrigo_runtime/
  setup_venv.bat
  app.py
  web_app.py
  audit_runtime.py
  runtime/
  data/
  logs/
  reports/
```

## Banco e pastas

O runtime usa SQLite como indice operacional em `data/0000-banco/0001-runtime.sqlite3`.

Todo evento tambem e espelhado em arquivos humanos:

```text
data/0005-operacoes/0001-eventos/0001-events.jsonl
data/0005-operacoes/0002-memorias/0001-memories.jsonl
data/0005-operacoes/0003-intervencoes/0001-interventions.jsonl
```

Isso permite que outras IAs leiam o estado sem precisar abrir o banco.

## GitHub

O botao de sincronizacao usa `git` local. Por padrao ele faz commit local do diretorio do runtime. Para push, configure um remoto no repositorio onde esta pasta estiver ou use:

```bat
set SAGE_RODRIGO_GITHUB_REMOTE=https://github.com/duEuler/Sage-duEuler.git
```

O push nunca deve esconder erro: a interface mostra stdout/stderr.
