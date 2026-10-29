"""Local HTTP boundary, static assets and endpoint adaptation."""
from __future__ import annotations

import json
from pathlib import Path
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .exports import csv_export


WEB = Path(__file__).resolve().parent.parent / 'web'
STATIC_ASSETS = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
    '/system.js': ('system.js', 'text/javascript; charset=utf-8'),
    '/prompts.js': ('prompts.js', 'text/javascript; charset=utf-8'),
    '/prompts.css': ('prompts.css', 'text/css; charset=utf-8'),
    '/help.js': ('help.js', 'text/javascript; charset=utf-8'),
    '/faq.html': ('faq.html', 'text/html; charset=utf-8'),
    '/pwa.js': ('pwa.js', 'text/javascript; charset=utf-8'),
    '/sw.js': ('sw.js', 'text/javascript; charset=utf-8'),
    '/style.css': ('style.css', 'text/css; charset=utf-8'),
    '/offline.html': ('offline.html', 'text/html; charset=utf-8'),
    '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
    '/icons/icon.svg': ('icons/icon.svg', 'image/svg+xml'),
    '/icons/icon-192.png': ('icons/icon-192.png', 'image/png'),
    '/icons/icon-512.png': ('icons/icon-512.png', 'image/png'),
    '/icons/maskable-512.png': ('icons/maskable-512.png', 'image/png'),
    '/icons/apple-touch-icon.png': ('icons/apple-touch-icon.png', 'image/png'),
}


class AppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, manager, system_info=None):
        super().__init__(address, Handler)
        self.manager = manager
        self.system_info = system_info
        self.token = secrets.token_urlsafe(32)
        self.allowed_hosts = {f'127.0.0.1:{self.server_port}', f'localhost:{self.server_port}'}


class Handler(BaseHTTPRequestHandler):
    server_version = 'OllamaBenchmark/1.0'

    def log_message(self, *_args):
        pass

    def send_data(self, status, body, content_type='application/json; charset=utf-8', filename=None):
        if not isinstance(body, bytes):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; manifest-src 'self'; worker-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json(self, status, value):
        self.send_data(status, json.dumps(value, ensure_ascii=False, allow_nan=False))

    def local_request(self):
        host = self.headers.get('Host', '')
        if host not in self.server.allowed_hosts:
            self.json(403, {'error': 'Host não autorizado. Use 127.0.0.1 ou localhost.'})
            return False
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + host:
            self.json(403, {'error': 'Origem não autorizada.'})
            return False
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.json(403, {'error': 'Origem não autorizada.'})
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        url = urlsplit(self.path)
        if url.path in STATIC_ASSETS:
            name, content_type = STATIC_ASSETS[url.path]
            body = (WEB / name).read_bytes()
            if url.path == '/':
                body = body.replace(b'__TOKEN__', self.server.token.encode('ascii'))
            self.send_data(200, body, content_type)
        elif url.path == '/api/state':
            self.json(200, self.server.manager.snapshot())
        elif url.path == '/api/system':
            if self.server.system_info is None:
                self.json(503, {'error': 'Resumo do ambiente indisponível nesta instância.'})
            else:
                try:
                    active = self.server.manager.is_active()
                    result = self.server.system_info.snapshot(busy=active)
                except Exception:
                    self.json(503, {'error': 'Resumo do ambiente indisponível nesta instância.'})
                else:
                    self.json(200, result)
        elif url.path == '/api/health':
            self.json(200, {'status': 'ok'})
        elif url.path == '/api/models':
            try:
                client = self.server.manager.client
                models = client.get('/api/tags')['models']
                loaded = client.get('/api/ps').get('models', [])
                self.json(200, {'models': models, 'loaded': loaded, 'ollama_url': client.base_url})
            except Exception as exc:
                self.json(502, {'error': 'Não foi possível acessar o Ollama local: ' + str(exc)})
        elif url.path == '/api/export':
            state = self.server.manager.snapshot()
            if parse_qs(url.query).get('format', ['json'])[0] == 'csv':
                self.send_data(200, csv_export(state), 'text/csv; charset=utf-8', 'ollama-benchmark.csv')
            else:
                self.send_data(200, json.dumps(state, indent=2, ensure_ascii=False, allow_nan=False), filename='ollama-benchmark.json')
        else:
            self.json(404, {'error': 'Não encontrado.'})

    def do_POST(self):
        if not self.local_request():
            return
        if not secrets.compare_digest(self.headers.get('X-Benchmark-Token', ''), self.server.token):
            self.json(403, {'error': 'Token da página inválido. Recarregue a página.'})
            return
        if self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
            self.json(415, {'error': 'Envie application/json com Content-Length.'})
            return
        try:
            size = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= size <= 65536:
                self.json(413, {'error': 'Corpo JSON excedeu 64 KiB ou tamanho ausente.'})
                return
            self.connection.settimeout(5)
            value = json.loads(self.rfile.read(size))
            if self.path == '/api/start':
                self.server.manager.start(value)
                self.json(202, {'status': 'running'})
            elif self.path == '/api/cancel':
                self.server.manager.cancel()
                self.json(200, {'status': self.server.manager.snapshot()['status']})
            else:
                self.json(404, {'error': 'Não encontrado.'})
        except (ValueError, UnicodeDecodeError) as exc:
            self.json(400, {'error': str(exc)})
        except RuntimeError as exc:
            self.json(409, {'error': str(exc)})
        except TimeoutError:
            self.json(408, {'error': 'Tempo de leitura do pedido excedido.'})
