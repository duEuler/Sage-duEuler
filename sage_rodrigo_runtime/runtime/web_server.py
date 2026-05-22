import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from runtime.engine import PresenceEngine
from runtime.reports import health_snapshot


ENGINE = PresenceEngine()


class RuntimeWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/events"):
            return self.send_json(ENGINE.store.latest_events(100))
        if self.path.startswith("/api/health"):
            return self.send_json(health_snapshot(ENGINE.store))
        return self.send_html(render_home())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = parse_qs(self.rfile.read(length).decode("utf-8"))
        try:
            if self.path == "/message":
                actor = data.get("actor", ["euler"])[0]
                message = data.get("message", [""])[0]
                result = ENGINE.add_message(actor, message)
            elif self.path == "/memory":
                actor = data.get("actor", ["euler"])[0]
                title = data.get("title", ["Memoria web"])[0]
                content = data.get("content", [""])[0]
                result = ENGINE.add_memory(actor, title, content)
            elif self.path == "/intervene":
                result = ENGINE.intervene("web", data.get("content", [""])[0])
            elif self.path == "/start":
                result = {"message": ENGINE.start()}
            elif self.path == "/pause":
                result = {"message": ENGINE.pause()}
            elif self.path == "/report":
                result = {"report": str(ENGINE.export_report())}
            else:
                result = {"error": "rota desconhecida"}
            return self.send_html(render_home(result))
        except Exception as exc:
            return self.send_html(render_home({"error": f"{type(exc).__name__}: {exc}"}))

    def send_json(self, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, body_text):
        body = body_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def render_home(result=None):
    snapshot = health_snapshot(ENGINE.store)
    result_html = f"<pre>{html.escape(json.dumps(result, ensure_ascii=False, indent=2))}</pre>" if result else ""
    events = "\n".join(
        f"<li><strong>{html.escape(event['actor'])}</strong> {html.escape(event['event_type'])}: {html.escape(event['title'])}</li>"
        for event in ENGINE.store.latest_events(50)
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Sage Rodrigo Runtime</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 32px; background: #f4f7f4; color: #102132; }}
    main {{ max-width: 1100px; margin: auto; }}
    textarea, input, select {{ width: 100%; padding: 10px; margin: 6px 0; }}
    button {{ padding: 10px 16px; margin: 6px 4px 6px 0; cursor: pointer; }}
    section {{ background: white; border: 1px solid #d9e4d9; border-radius: 16px; padding: 18px; margin-bottom: 16px; }}
    pre {{ background: #102132; color: #d6ffd8; padding: 12px; overflow: auto; }}
  </style>
</head>
<body>
<main>
  <h1>Sage Rodrigo Runtime</h1>
  <p>Modo: <strong>{html.escape(str(snapshot['mode']))}</strong> | eventos: {snapshot['latest_events']} | memorias: {snapshot['latest_memories']} | metas: {snapshot['goals']}</p>
  {result_html}
  <section>
    <form method="post" action="/message">
      <h2>Mensagem</h2>
      <select name="actor"><option>euler</option><option>sage</option><option>rodrigo</option><option>runtime</option></select>
      <textarea name="message" rows="4"></textarea>
      <button>Enviar</button>
    </form>
    <form method="post" action="/memory">
      <h2>Memoria</h2>
      <select name="actor"><option>euler</option><option>sage</option><option>rodrigo</option></select>
      <input name="title" placeholder="Titulo">
      <textarea name="content" rows="4"></textarea>
      <button>Registrar memoria</button>
    </form>
  </section>
  <section>
    <form method="post" action="/start"><button>Iniciar</button></form>
    <form method="post" action="/pause"><button>Pausar</button></form>
    <form method="post" action="/report"><button>Gerar relatorio</button></form>
    <form method="post" action="/intervene">
      <h2>Intervencao</h2>
      <textarea name="content" rows="3"></textarea>
      <button>Intervir</button>
    </form>
  </section>
  <section>
    <h2>Eventos recentes</h2>
    <ul>{events}</ul>
  </section>
</main>
</body>
</html>"""


def main(host="127.0.0.1", port=8765):
    server = HTTPServer((host, port), RuntimeWebHandler)
    print(f"Sage Rodrigo Runtime web em http://{host}:{port}")
    server.serve_forever()

