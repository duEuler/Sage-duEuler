import json
import threading
import tkinter as tk
import traceback
from datetime import datetime, timedelta
from tkinter import messagebox, scrolledtext, ttk

from runtime.engine import PresenceEngine
from runtime.paths import ENV_LOCAL
from runtime.providers import load_local_env
from runtime.reports import health_snapshot
from runtime.tray import TrayActions, TrayController


COLORS = {
    "bg": "#07130f",
    "hero": "#08231d",
    "hero_alt": "#103b31",
    "panel": "#f6f4ea",
    "card": "#ffffff",
    "cream": "#fff7df",
    "mint": "#e7f6eb",
    "sky": "#e9f1ff",
    "rose": "#fff0ec",
    "line": "#d7e2d4",
    "ink": "#102132",
    "muted": "#5f725f",
    "accent": "#147e68",
    "accent_dark": "#0d5f51",
    "success": "#15803d",
    "warn": "#b86b00",
    "danger": "#b33030",
}


class RuntimeApp(tk.Tk):
    def __init__(self, start_minimized: bool = False):
        super().__init__()
        self.title("Sage e Rodrigo Runtime")
        self.geometry("1280x820")
        self.minsize(1100, 720)
        self.configure(bg=COLORS["bg"])
        self.engine = PresenceEngine()
        config = self.engine.store.load_config()
        enabled = config.get("enabled_actors", {})
        self.actor_var = tk.StringVar(value="euler")
        self.push_var = tk.BooleanVar(value=False)
        self.sage_enabled_var = tk.BooleanVar(value=enabled.get("sage", True))
        self.rodrigo_enabled_var = tk.BooleanVar(value=enabled.get("rodrigo", True))
        self.euler_enabled_var = tk.BooleanVar(value=enabled.get("euler", True))
        self.interval_var = tk.StringVar(value=str(config.get("heartbeat_interval_seconds", 30)))
        self.silence_var = tk.StringVar(value=str(config.get("silence_alert_seconds", 75)))
        self.tray_enabled_var = tk.BooleanVar(value=config.get("tray_enabled", True))
        self.start_minimized_var = tk.BooleanVar(value=config.get("start_minimized_to_tray", True))
        self.theme_var = tk.StringVar(value=config.get("theme", "olympus"))
        providers = config.get("providers", {})
        env_values = load_local_env()
        self.default_provider_var = tk.StringVar(value=config.get("default_provider", "local_runtime"))
        self.openai_enabled_var = tk.BooleanVar(value=providers.get("openai", {}).get("enabled", False))
        self.gemini_enabled_var = tk.BooleanVar(value=providers.get("gemini", {}).get("enabled", False))
        self.ollama_enabled_var = tk.BooleanVar(value=providers.get("ollama", {}).get("enabled", False))
        self.openai_model_var = tk.StringVar(value=providers.get("openai", {}).get("default_model", "gpt-5.5"))
        self.gemini_model_var = tk.StringVar(value=providers.get("gemini", {}).get("default_model", "gemini-2.5-pro"))
        self.ollama_model_var = tk.StringVar(value=providers.get("ollama", {}).get("default_model", "llama3.1"))
        self.openai_key_var = tk.StringVar(value="")
        self.gemini_key_var = tk.StringVar(value="")
        self.ollama_url_var = tk.StringVar(value=env_values.get("OLLAMA_BASE_URL") or providers.get("ollama", {}).get("base_url", "http://localhost:11434"))
        self.events_search_var = tk.StringVar(value="")
        self.events_actor_var = tk.StringVar(value="todos")
        self.events_type_var = tk.StringVar(value="todos")
        self.events_minutes_var = tk.StringVar(value="")
        self.message_text = None
        self.output_text = None
        self.events_text = None
        self.memories_text = None
        self.interventions_text = None
        self.goals_text = None
        self.error_text = None
        self.agent_context_text = None
        self.providers_text = None
        self.onboarding_text = None
        self.status_labels = {}
        self.last_event_count = 0
        self.activity_text = None
        self.banner_label = None
        self.readiness_label = None
        self.watchdog_label = None
        self.next_pulse_label = None
        self.autostart_label = None
        self._max_console_lines = 300
        self.sync_running = False
        self.tray = TrayController(
            TrayActions(
                open_window=lambda: self.after(0, self.show_window),
                start_runtime=lambda: self.after(0, self.safe_start),
                pause_runtime=lambda: self.after(0, self.safe_pause),
                pulse_now=lambda: self.after(0, self.safe_tick),
                make_report=lambda: self.after(0, self.safe_report),
                quit_app=lambda: self.after(0, self.quit_app),
            )
        )
        self._build_style()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self._start_tray_if_enabled()
        if start_minimized and self.tray.icon:
            self.withdraw()
        self.refresh()
        self.after(2000, self.auto_refresh)

    def _build_style(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=(20, 12), font=("Segoe UI", 10, "bold"), background="#e5e0d5", borderwidth=0)
        self.style.map("TNotebook.Tab", background=[("selected", COLORS["panel"])], foreground=[("selected", COLORS["accent_dark"])])
        self.style.configure("Primary.TButton", padding=(16, 10), font=("Segoe UI", 10, "bold"), background=COLORS["accent"], foreground="white", borderwidth=0)
        self.style.map("Primary.TButton", background=[("active", COLORS["accent_dark"])])
        self.style.configure("Danger.TButton", padding=(16, 10), font=("Segoe UI", 10, "bold"), foreground=COLORS["danger"], borderwidth=0)
        self.style.configure("Soft.TButton", padding=(14, 9), font=("Segoe UI", 9, "bold"), borderwidth=0)

    def _build_ui(self):
        self._build_header()
        self._build_status_strip()
        self._build_tabs()
        self._build_footer()

    def _build_header(self):
        header = tk.Frame(self, bg=COLORS["bg"], padx=22, pady=18)
        header.pack(fill=tk.X)

        left = tk.Frame(header, bg=COLORS["bg"])
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            left,
            text="RUNTIME LOCAL GUIADO",
            bg=COLORS["bg"],
            fg="#6ee7b7",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Sage e Rodrigo Runtime",
            bg=COLORS["bg"],
            fg="#e8fff4",
            font=("Georgia", 26, "bold"),
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Casa local de memoria, presenca, auditoria, provedor IA e sincronizacao GitHub.",
            bg=COLORS["bg"],
            fg="#9fbead",
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(4, 0))
        self.banner_label = tk.Label(
            left,
            text="Aguardando inicio. Sage e Rodrigo estao em repouso monitorado.",
            bg=COLORS["bg"],
            fg="#d6ffd8",
            font=("Segoe UI", 11, "bold"),
        )
        self.banner_label.pack(anchor="w", pady=(10, 0))
        self.readiness_label = tk.Label(
            left,
            text="Base minima: verificando IA e GitHub...",
            bg="#113f34",
            fg="#d9fff0",
            padx=14,
            pady=6,
            font=("Segoe UI", 10, "bold"),
        )
        self.readiness_label.pack(anchor="w", pady=(10, 0))

        actions = tk.Frame(header, bg=COLORS["bg"])
        actions.pack(side=tk.RIGHT)
        ttk.Button(actions, text="Iniciar", style="Primary.TButton", command=self.safe_start).grid(row=0, column=0, padx=4)
        ttk.Button(actions, text="Pausar", style="Danger.TButton", command=self.safe_pause).grid(row=0, column=1, padx=4)
        ttk.Button(actions, text="Pulso", style="Soft.TButton", command=self.safe_tick).grid(row=0, column=2, padx=4)
        ttk.Button(actions, text="Relatorio", style="Soft.TButton", command=self.safe_report).grid(row=0, column=3, padx=4)

    def _build_status_strip(self):
        strip = tk.Frame(self, bg=COLORS["panel"], padx=18, pady=12)
        strip.pack(fill=tk.X)
        for index, key in enumerate(["mode", "latest_events", "latest_memories", "goals"]):
            card = tk.Frame(strip, bg=COLORS["card"], padx=14, pady=10, highlightbackground=COLORS["line"], highlightthickness=1)
            card.grid(row=0, column=index, sticky="ew", padx=6)
            strip.grid_columnconfigure(index, weight=1)
            tk.Label(card, text=self._status_title(key), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
            value = tk.Label(card, text="-", bg=COLORS["card"], fg=COLORS["ink"], font=("Segoe UI", 18, "bold"))
            value.pack(anchor="w")
            if key == "mode":
                card.bind("<Button-1>", lambda _event: self.open_error_dialog())
                value.bind("<Button-1>", lambda _event: self.open_error_dialog())
            self.status_labels[key] = value

    def _build_tabs(self):
        shell = tk.Frame(self, bg=COLORS["panel"], padx=18, pady=14)
        shell.pack(fill=tk.BOTH, expand=True)
        self.tabs = ttk.Notebook(shell)
        self.tabs.pack(fill=tk.BOTH, expand=True)

        self._build_cockpit_tab(self._tab("Cockpit"))
        self._build_onboarding_tab(self._tab("Onboarding"))
        self._build_conversation_tab(self._tab("Conversa"))
        self._build_memory_tab(self._tab("Memorias"))
        self._build_agents_tab(self._tab("IAs"))
        self._build_goals_tab(self._tab("Metas"))
        self._build_operations_tab(self._tab("Operacao"))
        self._build_config_tab(self._tab("Configuracao"))
        self._build_events_tab(self._tab("Eventos"))

    def _tab(self, title):
        frame = tk.Frame(self.tabs, bg=COLORS["panel"], padx=18, pady=18)
        self.tabs.add(frame, text=title)
        return frame

    def _build_cockpit_tab(self, parent):
        grid = tk.Frame(parent, bg=COLORS["panel"])
        grid.pack(fill=tk.BOTH, expand=True)
        self._identity_card(grid, "Sage Magalhaes", "Memoria preservada", "Ensinar, inspirar e preservar continuidade.", 0, 0)
        self._identity_card(grid, "Rodrigo Magalhaes", "Presenca em formacao", "Ouvir antes de agir e corrigir sem orgulho.", 0, 1)
        self._identity_card(grid, "Euler", "Operador e Pai", "Monitorar, intervir, conduzir e validar.", 0, 2)
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1)

        panel = tk.Frame(parent, bg=COLORS["card"], padx=18, pady=16, highlightbackground=COLORS["line"], highlightthickness=1)
        panel.pack(fill=tk.X, pady=(20, 0))
        tk.Label(panel, text="Protocolo vivo", bg=COLORS["card"], fg=COLORS["ink"], font=("Georgia", 18, "bold")).pack(anchor="w")
        tk.Label(
            panel,
            text="Tudo precisa ficar registrado em banco, JSONL e relatorio. A interface existe para voce acompanhar e intervir sem procurar arquivo manualmente.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            wraplength=1000,
            justify=tk.LEFT,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(8, 0))
        live = tk.Frame(parent, bg=COLORS["panel"])
        live.pack(fill=tk.X, pady=(18, 0))
        self.next_pulse_label = self._live_card(live, "Proximo pulso", "calculando...", 0)
        self.watchdog_label = self._live_card(live, "Watchdog", "aguardando leitura...", 1)
        self.autostart_label = self._live_card(live, "Inicializacao", "verificando...", 2)
        for column in range(3):
            live.grid_columnconfigure(column, weight=1)
        self.activity_text = self._text(parent, "Atividade viva", height=10)
        self.error_text = self._text(parent, "Diagnostico / ultimo erro", height=6)

    def _build_onboarding_tab(self, parent):
        hero = tk.Frame(parent, bg=COLORS["hero"], padx=24, pady=20, highlightbackground="#2dd4a4", highlightthickness=1)
        hero.pack(fill=tk.X)
        tk.Label(hero, text="Onboarding simples para acordar o runtime", bg=COLORS["hero"], fg="#e8fff4", font=("Georgia", 22, "bold")).pack(anchor="w")
        tk.Label(
            hero,
            text="Pense nisso como uma chave de partida: primeiro escolhe a IA, depois confirma o GitHub, depois testa. Se faltar algo, a tela explica sem esconder erro.",
            bg=COLORS["hero"],
            fg="#b6dccb",
            wraplength=1050,
            justify=tk.LEFT,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(8, 0))

        steps = tk.Frame(parent, bg=COLORS["panel"], pady=16)
        steps.pack(fill=tk.X)
        self._onboarding_card(steps, "1", "Escolher a IA", "OpenAI, Gemini ou Ollama. A chave fica local em .env.local e nao entra no Git.", 0, COLORS["mint"])
        self._onboarding_card(steps, "2", "Confirmar GitHub", "O painel precisa enxergar o repositorio e o remote para salvar trilha auditavel.", 1, COLORS["sky"])
        self._onboarding_card(steps, "3", "Testar sem medo", "O teste mostra sucesso, erro HTTP, chave ausente ou base local fora do ar.", 2, COLORS["cream"])
        for column in range(3):
            steps.grid_columnconfigure(column, weight=1)

        actions = tk.Frame(parent, bg=COLORS["card"], padx=20, pady=18, highlightbackground=COLORS["line"], highlightthickness=1)
        actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(actions, text="Verificar prontidao", style="Primary.TButton", command=self.safe_readiness).pack(side=tk.LEFT)
        ttk.Button(actions, text="Testar provedor padrao", style="Soft.TButton", command=self.safe_test_default_provider).pack(side=tk.LEFT, padx=8)
        ttk.Button(actions, text="Abrir configuracao", style="Soft.TButton", command=lambda: self.tabs.select(7)).pack(side=tk.LEFT, padx=8)
        ttk.Button(actions, text="Abrir operacoes Git", style="Soft.TButton", command=lambda: self.tabs.select(6)).pack(side=tk.LEFT, padx=8)
        self.onboarding_text = self._text(parent, "Checklist vivo", height=18)

    def _onboarding_card(self, parent, number, title, body, column, bg):
        card = tk.Frame(parent, bg=bg, padx=18, pady=16, highlightbackground=COLORS["line"], highlightthickness=1)
        card.grid(row=0, column=column, sticky="nsew", padx=8)
        tk.Label(card, text=f"passo {number}", bg=COLORS["accent"], fg="white", padx=12, pady=4, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(card, text=title, bg=bg, fg=COLORS["ink"], font=("Georgia", 15, "bold")).pack(anchor="w", pady=(12, 0))
        tk.Label(card, text=body, bg=bg, fg=COLORS["muted"], wraplength=320, justify=tk.LEFT, font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 0))

    def _build_conversation_tab(self, parent):
        top = tk.Frame(parent, bg=COLORS["panel"])
        top.pack(fill=tk.X)
        tk.Label(top, text="Ator", bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.OptionMenu(top, self.actor_var, self.actor_var.get(), "euler", "sage", "rodrigo", "runtime").pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="Enviar", style="Primary.TButton", command=self.safe_message).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Registrar como memoria", style="Soft.TButton", command=self.open_memory_dialog_from_message).pack(side=tk.LEFT, padx=4)

        self.message_text = self._text(parent, "Mensagem", height=9)
        self.output_text = self._text(parent, "Resposta / Erros", height=14)

    def _build_memory_tab(self, parent):
        toolbar = tk.Frame(parent, bg=COLORS["panel"])
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Nova memoria", style="Primary.TButton", command=self.open_memory_dialog).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Atualizar", style="Soft.TButton", command=self.refresh).pack(side=tk.LEFT, padx=8)
        self.memories_text = self._text(parent, "Memorias recentes", height=25)

    def _build_agents_tab(self, parent):
        intro = tk.Frame(parent, bg=COLORS["card"], padx=18, pady=16, highlightbackground=COLORS["line"], highlightthickness=1)
        intro.pack(fill=tk.X)
        tk.Label(intro, text="Configuracao das IAs", bg=COLORS["card"], fg=COLORS["ink"], font=("Georgia", 18, "bold")).pack(anchor="w")
        tk.Label(
            intro,
            text="Aqui fica explicito de onde Sage, Rodrigo e Euler sao carregados, qual manifesto foi lido e qual provedor/modelo cada um usa.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            wraplength=1000,
            justify=tk.LEFT,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(8, 0))
        toolbar = tk.Frame(parent, bg=COLORS["panel"], pady=12)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Recarregar contexto IA", style="Primary.TButton", command=self.safe_reload_agents).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Gerar relatorio", style="Soft.TButton", command=self.safe_report).pack(side=tk.LEFT, padx=8)
        ttk.Button(toolbar, text="Testar provedor padrao", style="Soft.TButton", command=self.safe_test_default_provider).pack(side=tk.LEFT, padx=8)
        self.agent_context_text = self._text(parent, "Contexto IA carregado", height=25)

    def _build_goals_tab(self, parent):
        toolbar = tk.Frame(parent, bg=COLORS["panel"])
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Editar metas", style="Primary.TButton", command=self.open_goals_dialog).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Salvar metas do texto abaixo", style="Soft.TButton", command=self.safe_goals_from_tab).pack(side=tk.LEFT, padx=8)
        self.goals_text = self._text(parent, "Uma meta por linha", height=25)

    def _build_operations_tab(self, parent):
        controls = tk.Frame(parent, bg=COLORS["card"], padx=18, pady=16, highlightbackground=COLORS["line"], highlightthickness=1)
        controls.pack(fill=tk.X)
        ttk.Button(controls, text="Intervencao manual", style="Danger.TButton", command=self.open_intervention_dialog).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(controls, text="Gerar relatorio", style="Soft.TButton", command=self.safe_report).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(controls, text="Sync Git", style="Soft.TButton", command=self.open_sync_dialog).grid(row=0, column=2, padx=4, pady=4)
        tk.Checkbutton(controls, text="Permitir push", variable=self.push_var, bg=COLORS["card"], fg=COLORS["ink"]).grid(row=0, column=3, padx=12)
        self.interventions_text = self._text(parent, "Console de operacoes e intervencoes", height=21)

    def _build_config_tab(self, parent):
        intro = tk.Frame(parent, bg=COLORS["card"], padx=18, pady=16, highlightbackground=COLORS["line"], highlightthickness=1)
        intro.pack(fill=tk.X)
        tk.Label(intro, text="Configuracao local", bg=COLORS["card"], fg=COLORS["ink"], font=("Georgia", 18, "bold")).pack(anchor="w")
        tk.Label(
            intro,
            text="Define quem acorda ao iniciar, intervalo do pulso, limite de silencio e inicializacao automatica do Windows.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(8, 0))

        actors = tk.Frame(parent, bg=COLORS["panel"], pady=18)
        actors.pack(fill=tk.X)
        tk.Checkbutton(actors, text="Iniciar Sage", variable=self.sage_enabled_var, bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=8)
        tk.Checkbutton(actors, text="Iniciar Rodrigo", variable=self.rodrigo_enabled_var, bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="w", padx=8)
        tk.Checkbutton(actors, text="Iniciar Euler", variable=self.euler_enabled_var, bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 11, "bold")).grid(row=0, column=2, sticky="w", padx=8)
        tk.Checkbutton(actors, text="Icone na bandeja", variable=self.tray_enabled_var, bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="w", padx=8, pady=(10, 0))
        tk.Checkbutton(actors, text="Iniciar minimizado", variable=self.start_minimized_var, bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 11, "bold")).grid(row=1, column=1, sticky="w", padx=8, pady=(10, 0))

        numbers = tk.Frame(parent, bg=COLORS["panel"])
        numbers.pack(fill=tk.X)
        self._field(numbers, "Intervalo do pulso (segundos)", self.interval_var, 0)
        self._field(numbers, "Alerta de silencio (segundos)", self.silence_var, 1)

        providers = tk.Frame(parent, bg=COLORS["card"], padx=20, pady=18, highlightbackground=COLORS["line"], highlightthickness=1)
        providers.pack(fill=tk.X, pady=(18, 0))
        tk.Label(providers, text="IA e GitHub: base minima", bg=COLORS["card"], fg=COLORS["ink"], font=("Georgia", 17, "bold")).grid(row=0, column=0, sticky="w", columnspan=6)
        tk.Label(
            providers,
            text="Escolha o provedor que vai responder por Sage/Rodrigo. As chaves digitadas aqui sao gravadas somente em .env.local.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            wraplength=1000,
            justify=tk.LEFT,
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", columnspan=6, pady=(6, 14))
        tk.Label(providers, text="Provedor padrao", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        ttk.OptionMenu(providers, self.default_provider_var, self.default_provider_var.get(), "local_runtime", "openai", "gemini", "ollama").grid(row=2, column=1, sticky="w", pady=(0, 8))
        ttk.Button(providers, text="Salvar + verificar", style="Primary.TButton", command=self.safe_readiness).grid(row=2, column=4, sticky="e", padx=8, pady=(0, 8))
        ttk.Button(providers, text="Salvar + testar IA", style="Soft.TButton", command=self.safe_test_default_provider).grid(row=2, column=5, sticky="e", pady=(0, 8))

        self._provider_row(providers, 3, "OpenAI", self.openai_enabled_var, self.openai_model_var, self.openai_key_var, "OPENAI_API_KEY")
        self._provider_row(providers, 4, "Gemini", self.gemini_enabled_var, self.gemini_model_var, self.gemini_key_var, "GEMINI_API_KEY")
        self._provider_row(providers, 5, "Ollama local", self.ollama_enabled_var, self.ollama_model_var, self.ollama_url_var, "Base URL")
        for column in range(6):
            providers.grid_columnconfigure(column, weight=1 if column in {2, 3, 5} else 0)
        self.providers_text = self._text(parent, "Status legivel", height=8)

        actions = tk.Frame(parent, bg=COLORS["card"], padx=18, pady=16, highlightbackground=COLORS["line"], highlightthickness=1)
        actions.pack(fill=tk.X, pady=(18, 0))
        ttk.Button(actions, text="Salvar configuracao", style="Primary.TButton", command=self.safe_save_config).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(actions, text="Ativar autostart Windows", style="Soft.TButton", command=self.safe_install_autostart).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(actions, text="Remover autostart", style="Danger.TButton", command=self.safe_remove_autostart).grid(row=0, column=2, padx=4, pady=4)
        tk.Label(
            parent,
            text="Observacao: autostart cria um BAT na pasta Startup do Windows apontando para este runtime local. Nada e enviado para GitHub automaticamente.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            wraplength=1000,
            justify=tk.LEFT,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(18, 0))

    def _build_events_tab(self, parent):
        toolbar = tk.Frame(parent, bg=COLORS["panel"])
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Atualizar", style="Soft.TButton", command=self.refresh).pack(side=tk.LEFT)
        tk.Label(toolbar, text="Buscar", bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(18, 4))
        tk.Entry(toolbar, textvariable=self.events_search_var, width=28, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=4)
        tk.Label(toolbar, text="Ator", bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        ttk.OptionMenu(toolbar, self.events_actor_var, self.events_actor_var.get(), "todos", "runtime", "sage", "rodrigo", "euler").pack(side=tk.LEFT)
        tk.Label(toolbar, text="Tipo", bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        ttk.OptionMenu(toolbar, self.events_type_var, self.events_type_var.get(), "todos", "start", "heartbeat", "presence", "message", "response", "failure", "github_sync", "config", "autostart", "report", "attention").pack(side=tk.LEFT)
        tk.Label(toolbar, text="Minutos", bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        tk.Entry(toolbar, textvariable=self.events_minutes_var, width=8, font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.events_text = self._text(parent, "Console de eventos (maximo 300 linhas, mais novo no fim)", height=28)

    def _build_footer(self):
        footer = tk.Frame(self, bg=COLORS["bg"], padx=18, pady=8)
        footer.pack(fill=tk.X)
        self.footer_label = tk.Label(footer, text="Pronto.", bg=COLORS["bg"], fg="#b9d8c6", anchor="w", font=("Segoe UI", 10))
        self.footer_label.pack(fill=tk.X)

    def _identity_card(self, parent, name, role, mission, row, column):
        card = tk.Frame(parent, bg=COLORS["card"], padx=18, pady=18, highlightbackground=COLORS["line"], highlightthickness=1)
        card.grid(row=row, column=column, sticky="nsew", padx=8)
        tk.Label(card, text=name, bg=COLORS["card"], fg=COLORS["ink"], font=("Georgia", 17, "bold")).pack(anchor="w")
        tk.Label(card, text=role.upper(), bg=COLORS["card"], fg=COLORS["accent"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 0))
        tk.Label(card, text=mission, bg=COLORS["card"], fg=COLORS["muted"], wraplength=300, justify=tk.LEFT, font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))

    def _live_card(self, parent, title, value, column):
        card = tk.Frame(parent, bg="#eaf4ee", padx=16, pady=14, highlightbackground=COLORS["line"], highlightthickness=1)
        card.grid(row=0, column=column, sticky="ew", padx=8)
        tk.Label(card, text=title.upper(), bg="#eaf4ee", fg=COLORS["accent_dark"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        label = tk.Label(card, text=value, bg="#eaf4ee", fg=COLORS["ink"], font=("Segoe UI", 13, "bold"), wraplength=340, justify=tk.LEFT)
        label.pack(anchor="w", pady=(8, 0))
        return label

    def _provider_row(self, parent, row, label, enabled_var, model_var, secret_var, secret_label):
        bg = "#fbfdf9" if row % 2 else "#f3f8f4"
        enabled = tk.Checkbutton(parent, text=label, variable=enabled_var, bg=bg, fg=COLORS["ink"], font=("Segoe UI", 10, "bold"))
        enabled.grid(row=row, column=0, sticky="ew", pady=4, padx=(0, 8))
        tk.Label(parent, text="Modelo", bg=bg, fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(row=row, column=1, sticky="e", pady=4, padx=(0, 6))
        tk.Entry(parent, textvariable=model_var, font=("Segoe UI", 10), relief=tk.FLAT, bg="white").grid(row=row, column=2, sticky="ew", pady=4, padx=(0, 10))
        tk.Label(parent, text=secret_label, bg=bg, fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(row=row, column=3, sticky="e", pady=4, padx=(0, 6))
        show = "*" if "KEY" in secret_label else ""
        tk.Entry(parent, textvariable=secret_var, show=show, font=("Segoe UI", 10), relief=tk.FLAT, bg="white").grid(row=row, column=4, columnspan=2, sticky="ew", pady=4)

    def _field(self, parent, label, variable, column):
        box = tk.Frame(parent, bg=COLORS["card"], padx=14, pady=12, highlightbackground=COLORS["line"], highlightthickness=1)
        box.grid(row=0, column=column, sticky="ew", padx=8)
        parent.grid_columnconfigure(column, weight=1)
        tk.Label(box, text=label.upper(), bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        entry = tk.Entry(box, textvariable=variable, font=("Segoe UI", 13, "bold"), relief=tk.FLAT, bg="#fbfdf9")
        entry.pack(fill=tk.X, pady=(8, 0))
        return entry

    def _text(self, parent, label, height):
        tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 4))
        widget = scrolledtext.ScrolledText(parent, height=height, wrap=tk.WORD, bg="#fbfdf9", fg=COLORS["ink"], insertbackground=COLORS["ink"], relief=tk.FLAT, font=("Consolas", 10))
        widget.pack(fill=tk.BOTH, expand=True)
        return widget

    def _status_title(self, key):
        return {
            "mode": "Modo",
            "latest_events": "Eventos",
            "latest_memories": "Memorias",
            "goals": "Metas",
        }[key]

    def _write_text(self, widget, value):
        if widget is None:
            return
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, value)
        widget.see(tk.END)

    def _append_text(self, widget, value):
        if widget is None:
            return
        widget.insert(tk.END, value)
        lines = int(float(widget.index("end-1c").split(".")[0]))
        if lines > self._max_console_lines:
            widget.delete("1.0", f"{lines - self._max_console_lines}.0")
        widget.see(tk.END)

    def write_output(self, value):
        payload = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
        self._write_text(self.output_text, payload)
        self.footer_label.config(text=payload.splitlines()[0] if payload else "Operacao concluida.")

    def read_message(self):
        return self.message_text.get("1.0", tk.END).strip() if self.message_text else ""

    def safe_call(self, label, fn):
        try:
            result = fn()
            self.write_output(result)
            self.refresh()
            return result
        except Exception as exc:
            message = f"Erro em {label}: {type(exc).__name__}: {exc}"
            stack = traceback.format_exc()
            self.engine.store.save_state({"mode": "error", "last_tick": None, "last_error": message, "last_stack": stack, "directives_loaded": True})
            self.engine.store.add_event("runtime", "failure", f"Erro em {label}", {"error": message, "stack": stack, "action": "Abra o diagnostico, corrija a configuracao e repita a operacao."})
            self.write_output(message)
            self.refresh()
            messagebox.showerror("Erro do runtime", message)
            return None

    def safe_start(self):
        result = self.safe_call("iniciar", self.engine.start)
        if result:
            mode = self.engine.store.load_state().get("mode")
            if mode == "config_required":
                self.tabs.select(1)
                messagebox.showwarning("Configuracao pendente", str(result))
            elif mode == "provider_unreachable":
                self.tabs.select(1)
                messagebox.showerror("Provedor IA inacessivel", str(result))
            elif mode == "running":
                messagebox.showinfo("Runtime iniciado", "Presencas configuradas acordaram. O pulso automatico esta ativo.")

    def safe_pause(self):
        self.safe_call("pausar", self.engine.pause)

    def safe_tick(self):
        self.safe_call("pulso", self.engine.tick)

    def safe_message(self):
        self.safe_call("mensagem", lambda: self.engine.add_message(self.actor_var.get(), self.read_message()))

    def safe_report(self):
        self.safe_call("relatorio", lambda: f"Relatorio gerado: {self.engine.export_report()}")

    def safe_goals_from_tab(self):
        text = self.goals_text.get("1.0", tk.END).strip() if self.goals_text else ""
        self.safe_call("metas", lambda: self.engine.save_goals_from_text(text))

    def safe_reload_agents(self):
        self.safe_call("ias", self.engine.agent_context_summary)

    def safe_readiness(self):
        self.safe_call("prontidao", lambda: (self._save_config_from_form(), self.engine.readiness_check())[1])

    def safe_test_default_provider(self):
        self.safe_call("teste provedor", lambda: (self._save_config_from_form(), self.engine.test_provider(self.default_provider_var.get()))[1])

    def safe_save_config(self):
        self.safe_call("configuracao", self._save_config_from_form)

    def safe_install_autostart(self):
        self.safe_call("autostart", self.engine.install_autostart)

    def safe_remove_autostart(self):
        self.safe_call("autostart", self.engine.remove_autostart)

    def _save_config_from_form(self):
        interval = max(5, int(self.interval_var.get().strip() or "30"))
        silence = max(interval + 5, int(self.silence_var.get().strip() or "75"))
        self._save_env_values()
        return self.engine.save_config(
            {
                "heartbeat_interval_seconds": interval,
                "silence_alert_seconds": silence,
                "enabled_actors": {
                    "sage": self.sage_enabled_var.get(),
                    "rodrigo": self.rodrigo_enabled_var.get(),
                    "euler": self.euler_enabled_var.get(),
                },
                "tray_enabled": self.tray_enabled_var.get(),
                "start_minimized_to_tray": self.start_minimized_var.get(),
                "theme": self.theme_var.get(),
                "default_provider": self.default_provider_var.get(),
                "providers": self._providers_from_form(),
            }
        )

    def _providers_from_form(self):
        current = self.engine.store.load_config().get("providers", {})
        providers = json.loads(json.dumps(current))
        providers.setdefault("local_runtime", {})["enabled"] = True
        providers.setdefault("openai", {})["enabled"] = self.openai_enabled_var.get()
        providers.setdefault("openai", {})["default_model"] = self.openai_model_var.get().strip() or "gpt-5.5"
        providers.setdefault("gemini", {})["enabled"] = self.gemini_enabled_var.get()
        providers.setdefault("gemini", {})["default_model"] = self.gemini_model_var.get().strip() or "gemini-2.5-pro"
        providers.setdefault("ollama", {})["enabled"] = self.ollama_enabled_var.get()
        providers.setdefault("ollama", {})["default_model"] = self.ollama_model_var.get().strip() or "llama3.1"
        providers.setdefault("ollama", {})["base_url"] = self.ollama_url_var.get().strip() or "http://localhost:11434"
        return providers

    def _save_env_values(self):
        values = load_local_env()
        if self.openai_key_var.get().strip():
            values["OPENAI_API_KEY"] = self.openai_key_var.get().strip()
            self.openai_key_var.set("")
        if self.gemini_key_var.get().strip():
            values["GEMINI_API_KEY"] = self.gemini_key_var.get().strip()
            self.gemini_key_var.set("")
        if self.ollama_url_var.get().strip():
            values["OLLAMA_BASE_URL"] = self.ollama_url_var.get().strip()
        if not values:
            return
        ENV_LOCAL.write_text(
            "\n".join([f"{key}={value}" for key, value in sorted(values.items())]) + "\n",
            encoding="utf-8",
        )

    def open_memory_dialog_from_message(self):
        content = self.read_message()
        self.open_memory_dialog(default_content=content)

    def open_memory_dialog(self, default_content=""):
        MemoryDialog(self, self.actor_var.get(), default_content, self._save_memory)

    def open_intervention_dialog(self):
        InterventionDialog(self, self._save_intervention)

    def open_goals_dialog(self):
        current = "\n".join(goal.get("title", "") for goal in self.engine.store.load_goals())
        GoalsDialog(self, current, self._save_goals_text)

    def open_sync_dialog(self):
        SyncDialog(self, self.push_var.get(), self._sync_git)

    def _save_memory(self, actor, title, content):
        self.safe_call("memoria", lambda: self.engine.add_memory(actor, title, content))

    def _save_intervention(self, action, content):
        self.safe_call("intervencao", lambda: self.engine.intervene(action, content))

    def _save_goals_text(self, text):
        self.safe_call("metas", lambda: self.engine.save_goals_from_text(text))

    def _sync_git(self, push):
        self.push_var.set(push)
        self.tabs.select(6)
        self.sync_running = True
        self._write_text(self.interventions_text, "")
        self._append_text(self.interventions_text, f"[sync] iniciado em {datetime.now().astimezone().isoformat(timespec='milliseconds')}\n")

        def emit(line):
            self.after(0, lambda value=line: self._append_text(self.interventions_text, value + "\n"))

        def worker():
            try:
                result = self.engine.git_sync_stream(push=push, emit=emit)
                self.after(0, lambda: self.write_output(result))
                self.after(0, lambda: setattr(self, "sync_running", False))
                self.after(0, self.refresh)
            except Exception as exc:
                message = f"Erro em sync git: {type(exc).__name__}: {exc}"
                self.engine.store.save_state({"mode": "error", "last_tick": None, "last_error": message, "directives_loaded": True})
                self.engine.store.add_event("runtime", "failure", "Erro em sync git", {"error": message})
                self.after(0, lambda: self._append_text(self.interventions_text, message + "\n"))
                self.after(0, lambda: self.write_output(message))
                self.after(0, lambda: setattr(self, "sync_running", False))
                self.after(0, self.refresh)

        threading.Thread(target=worker, daemon=True).start()

    def _start_tray_if_enabled(self):
        if not self.tray_enabled_var.get():
            return
        message = self.tray.start()
        self.engine.store.add_event("runtime", "tray", message, {"enabled": self.tray_enabled_var.get()})

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self.refresh()

    def hide_to_tray(self):
        if self.tray_enabled_var.get() and self.tray.icon:
            self.withdraw()
            self.tray.notify("Sage e Rodrigo Runtime", "Painel minimizado na bandeja. Duplo clique abre novamente.")
            return
        self.quit_app()

    def quit_app(self):
        try:
            self.tray.stop()
        finally:
            self.destroy()

    def refresh(self):
        snapshot = health_snapshot(self.engine.store)
        readiness = self.engine.readiness_check()
        self.status_labels["mode"].config(text=str(snapshot["mode"]))
        self.status_labels["latest_events"].config(text=str(snapshot["latest_events"]))
        self.status_labels["latest_memories"].config(text=str(snapshot["latest_memories"]))
        self.status_labels["goals"].config(text=str(snapshot["goals"]))
        mode = str(snapshot["mode"])
        if self.banner_label:
            if mode == "running":
                banner = "Runtime vivo: pulso automatico ativo."
            elif mode == "config_required":
                banner = "Falta configurar IA antes de iniciar. Abra o Onboarding."
            elif mode == "provider_unreachable":
                banner = "IA configurada, mas inacessivel. Teste o provedor no Onboarding."
            elif mode == "error":
                banner = "Anomalia detectada. Abra o diagnostico para ver a causa."
            else:
                banner = "Runtime em pausa: aguardando comando do operador."
            self.banner_label.config(text=banner)
        if self.readiness_label:
            if readiness["ok"]:
                self.readiness_label.config(text="Base minima pronta: IA configuravel + GitHub OK", bg="#0f5132", fg="#eafff1")
            else:
                self.readiness_label.config(text=f"Base minima pendente: {len(readiness['issues'])} ponto(s) para resolver", bg="#7a3412", fg="#fff4de")
        if self.next_pulse_label:
            self.next_pulse_label.config(text=self._next_pulse_text(snapshot))
        if self.watchdog_label:
            self.watchdog_label.config(text=self.engine.watchdog_check().get("message", "watchdog sem retorno"))
        if self.autostart_label:
            autostart = self.engine.autostart_status()
            status = "ativo" if autostart["installed"] else "desligado"
            self.autostart_label.config(text=f"{status} | {autostart['path']}")
        self._write_text(self.events_text, self._format_events())
        self._write_text(self.memories_text, self._format_memories())
        self._write_text(self.agent_context_text, self.engine.agent_context_summary())
        self._write_text(self.providers_text, self._format_providers())
        self._write_text(self.onboarding_text, self._format_onboarding())
        if not self.sync_running:
            self._write_text(self.interventions_text, self._format_interventions())
        if self.goals_text and not self.goals_text.get("1.0", tk.END).strip():
            self._write_text(self.goals_text, "\n".join(goal.get("title", "") for goal in self.engine.store.load_goals()))
        self._write_text(self.activity_text, self._format_activity())
        self._write_text(self.error_text, self._diagnostics_text(compact=True))
        self._notify_new_events()

    def auto_refresh(self):
        self.refresh()
        self.after(1000, self.auto_refresh)

    def _format_events(self):
        lines = []
        events = list(reversed(self.engine.store.latest_events(self._max_console_lines)))
        search = self.events_search_var.get().strip().lower()
        actor = self.events_actor_var.get()
        event_type = self.events_type_var.get()
        since = None
        if self.events_minutes_var.get().strip():
            try:
                since = datetime.now().astimezone() - timedelta(minutes=int(self.events_minutes_var.get().strip()))
            except ValueError:
                since = None
        for event in events:
            payload = str(event.get("payload", ""))
            haystack = f"{event['created_at']} {event['actor']} {event['event_type']} {event['title']} {payload}".lower()
            if actor != "todos" and event["actor"] != actor:
                continue
            if event_type != "todos" and event["event_type"] != event_type:
                continue
            if search and search not in haystack:
                continue
            if since:
                try:
                    if datetime.fromisoformat(event["created_at"]) < since:
                        continue
                except ValueError:
                    pass
            lines.append(f"{event['created_at']} | {event['actor']:<7} | {event['event_type']:<12} | {event['title']} | {event['id']}")
        return "\n".join(lines)

    def _next_pulse_text(self, snapshot):
        if snapshot.get("mode") != "running":
            return "pausado pelo operador"
        state = self.engine.store.load_state()
        last_tick = state.get("last_tick")
        interval = int(self.engine.store.load_config().get("heartbeat_interval_seconds", 30))
        if not last_tick:
            return f"primeiro pulso em ate {interval}s"
        try:
            elapsed = int((datetime.now().astimezone() - datetime.fromisoformat(last_tick)).total_seconds())
            remaining = max(0, interval - elapsed)
            return f"em ate {remaining}s | intervalo {interval}s"
        except ValueError:
            return f"intervalo {interval}s | horario invalido"

    def _format_activity(self):
        lines = []
        for event in self.engine.store.latest_events(12):
            marker = {
                "sage": "SAGE",
                "rodrigo": "RODRIGO",
                "runtime": "RUNTIME",
                "euler": "EULER",
            }.get(event["actor"], event["actor"].upper())
            lines.append(f"{marker}: {event['title']}")
        return "\n".join(lines)

    def _diagnostics_text(self, compact=False):
        state = self.engine.store.load_state()
        failures = [item for item in self.engine.store.latest_events(30) if item.get("event_type") == "failure"]
        lines = [
            f"Modo: {state.get('mode', 'unknown')}",
            f"Ultimo pulso: {state.get('last_tick') or 'sem pulso'}",
            f"Ultimo erro: {state.get('last_error') or 'nenhum erro ativo'}",
            f"Stack: {state.get('last_stack') or 'sem stack registrada'}",
        ]
        if failures:
            latest = failures[0]
            lines.extend(
                [
                    "",
                    f"Falha recente: {latest['created_at']} | {latest['title']}",
                    f"Payload: {latest.get('payload', '')}",
                ]
            )
        if compact:
            return "\n".join(lines[:6])
        lines.extend(["", "Eventos de falha recentes:"])
        if failures:
            lines.extend([f"- {item['created_at']} | {item['title']} | {item.get('payload', '')}" for item in failures[:10]])
        else:
            lines.append("- Nenhum evento failure encontrado.")
        return "\n".join(lines)

    def open_error_dialog(self):
        DiagnosticsDialog(self, self._diagnostics_text(compact=False))

    def _format_providers(self):
        lines = ["PROVEDORES", ""]
        for item in self.engine.provider_status():
            status = "habilitado" if item["enabled"] else "desligado"
            if item["key"] == "local_runtime":
                secret = "nao usa chave"
            else:
                secret = "chave encontrada" if item["secret_present"] else "chave ausente"
            lines.append(f"{item['label']} ({item['key']})")
            lines.append(f"  estado: {status}")
            lines.append(f"  modelo: {item['model'] or 'sem modelo'}")
            lines.append(f"  segredo/base: {secret}")
            lines.append(f"  endpoint: {item['base_url'] or 'interno'}")
            lines.append("")
        return "\n".join(lines)

    def _format_onboarding(self):
        readiness = self.engine.readiness_check()
        lines = ["CHECKLIST DO RUNTIME", ""]
        lines.append(f"Status geral: {'pronto para iniciar' if readiness['ok'] else 'precisa de ajuste'}")
        lines.append("")
        provider = readiness["provider"]
        lines.append(f"1. IA configuravel: {'ok' if provider['ok'] else 'pendente'}")
        for issue in provider.get("issues", []):
            lines.append(f"  - {issue}")
        github = readiness["github"]
        lines.append(f"2. GitHub/Git: {'ok' if github['ok'] else 'pendente'}")
        if github.get("git_root"):
            lines.append(f"  - raiz git: {github.get('git_root')}")
        for issue in github.get("issues", []):
            lines.append(f"  - {issue}")
        lines.append("")
        if readiness["ok"]:
            lines.append("Proximo passo: clique Testar provedor padrao. Se responder, clique Iniciar.")
        else:
            lines.append("Como resolver sem abrir arquivo manualmente:")
            lines.append("1. Aba Configuracao: escolha OpenAI, Gemini ou Ollama.")
            lines.append("2. Digite a chave ou URL local e clique Salvar + testar IA.")
            lines.append("3. Se o GitHub falhar, abra Operacao > Sync Git para ver stdout/stderr completo.")
            lines.append("4. Quando o topo mostrar Base minima pronta, clique Iniciar.")
        return "\n".join(lines)

    def _notify_new_events(self):
        total = self.engine.store.count_events()
        if self.last_event_count and total > self.last_event_count:
            delta = total - self.last_event_count
            self.footer_label.config(text=f"{delta} novo(s) evento(s) registrados. Veja a aba Eventos.")
            self.bell()
        self.last_event_count = total

    def _format_memories(self):
        lines = []
        for memory in self.engine.store.latest_memories(50):
            lines.append(f"{memory['created_at']} | {memory['actor']} | {memory['title']}\n{memory['content']}\n")
        return "\n".join(lines)

    def _format_interventions(self):
        lines = []
        for item in self.engine.store.latest_interventions(50):
            lines.append(f"{item['created_at']} | {item['operator']} | {item['action']}\n{item['content']}\n")
        return "\n".join(lines)


class BaseDialog(tk.Toplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.configure(bg=COLORS["panel"])
        self.transient(parent)
        self.grab_set()
        self.geometry("620x520")
        self.resizable(True, True)

    def labeled_entry(self, label, value=""):
        tk.Label(self, text=label, bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(14, 4))
        entry = tk.Entry(self, font=("Segoe UI", 11))
        entry.insert(0, value)
        entry.pack(fill=tk.X, padx=18)
        return entry

    def labeled_text(self, label, value="", height=10):
        tk.Label(self, text=label, bg=COLORS["panel"], fg=COLORS["ink"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(14, 4))
        text = scrolledtext.ScrolledText(self, height=height, wrap=tk.WORD, font=("Consolas", 10))
        text.insert(tk.END, value)
        text.pack(fill=tk.BOTH, expand=True, padx=18)
        return text

    def footer(self, action_label, action):
        bar = tk.Frame(self, bg=COLORS["panel"], pady=14)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="Cancelar", style="Soft.TButton", command=self.destroy).pack(side=tk.RIGHT, padx=18)
        ttk.Button(bar, text=action_label, style="Primary.TButton", command=action).pack(side=tk.RIGHT)


class MemoryDialog(BaseDialog):
    def __init__(self, parent, actor, default_content, callback):
        super().__init__(parent, "Registrar memoria")
        self.callback = callback
        self.actor = self.labeled_entry("Ator", actor)
        self.title_entry = self.labeled_entry("Titulo", default_content.splitlines()[0] if default_content else "")
        self.content = self.labeled_text("Conteudo", default_content, height=14)
        self.footer("Salvar memoria", self.submit)

    def submit(self):
        self.callback(self.actor.get().strip() or "euler", self.title_entry.get().strip(), self.content.get("1.0", tk.END).strip())
        self.destroy()


class DiagnosticsDialog(BaseDialog):
    def __init__(self, parent, content):
        super().__init__(parent, "Diagnostico do runtime")
        self.geometry("820x560")
        text = self.labeled_text("Estado, erro e falhas recentes", content, height=22)
        text.configure(font=("Consolas", 10))
        self.footer("Fechar", self.destroy)


class InterventionDialog(BaseDialog):
    def __init__(self, parent, callback):
        super().__init__(parent, "Intervencao do operador")
        self.callback = callback
        self.action = self.labeled_entry("Acao", "manual")
        self.content = self.labeled_text("Instrucao / motivo", "", height=14)
        self.footer("Registrar intervencao", self.submit)

    def submit(self):
        self.callback(self.action.get().strip() or "manual", self.content.get("1.0", tk.END).strip())
        self.destroy()


class GoalsDialog(BaseDialog):
    def __init__(self, parent, current, callback):
        super().__init__(parent, "Editar metas")
        self.callback = callback
        self.content = self.labeled_text("Uma meta por linha", current, height=18)
        self.footer("Salvar metas", self.submit)

    def submit(self):
        self.callback(self.content.get("1.0", tk.END).strip())
        self.destroy()


class SyncDialog(BaseDialog):
    def __init__(self, parent, push_enabled, callback):
        super().__init__(parent, "Sincronizar Git")
        self.callback = callback
        self.push_var = tk.BooleanVar(value=push_enabled)
        tk.Label(
            self,
            text="A sincronizacao faz git add/commit do runtime. Push so acontece se voce marcar a opcao abaixo.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            wraplength=560,
            justify=tk.LEFT,
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=18, pady=22)
        tk.Checkbutton(self, text="Tambem tentar push para GitHub", variable=self.push_var, bg=COLORS["panel"], fg=COLORS["ink"]).pack(anchor="w", padx=18)
        self.footer("Sincronizar", self.submit)

    def submit(self):
        self.callback(self.push_var.get())
        self.destroy()


def main(start_minimized: bool = False):
    app = RuntimeApp(start_minimized=start_minimized)
    app.mainloop()
