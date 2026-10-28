"""Local Ollama HTTP transport and streamed measurements."""
from __future__ import annotations

import http.client
import json
import socket
import threading
import time
from urllib.parse import urlsplit

from .metrics import metrics


class Cancelled(Exception):
    """The caller cancelled a measurement."""


class OllamaClient:
    def __init__(self, base_url='http://127.0.0.1:11434'):
        url = urlsplit(base_url)
        if url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost', '::1', 'host.docker.internal'} or url.username or url.password or url.path not in {'', '/'} or url.query or url.fragment:
            raise ValueError('OLLAMA_URL precisa apontar para o Ollama local por HTTP.')
        self.host, self.port = url.hostname, url.port or 11434
        self.base_url = base_url.rstrip('/')
        self._lock = threading.Lock()
        self._active = None
        self._socket = None

    def get(self, path):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        response = None
        try:
            conn.request('GET', path)
            response = conn.getresponse()
            body = response.read(4 * 1024 * 1024 + 1)
            if response.status != 200:
                raise ValueError(f'Ollama HTTP {response.status}.')
            if len(body) > 4 * 1024 * 1024:
                raise ValueError('Resposta do Ollama excedeu o limite.')
            return json.loads(body)
        finally:
            if response is not None:
                response.close()
            conn.close()

    def cancel(self):
        with self._lock:
            conn = self._active
            if self._socket is not None:
                try:
                    self._socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            if conn is not None:
                conn.close()

    def generate(self, model, settings, cancel_event):
        started = time.perf_counter()
        deadline = started + settings['timeout']
        conn = http.client.HTTPConnection(self.host, self.port, timeout=settings['timeout'])
        with self._lock:
            self._active = conn
        first_content = first_text = final = None
        response = None
        text = ''
        expired = threading.Event()

        def expire():
            expired.set()
            with self._lock:
                if self._active is conn:
                    target = self._socket or conn.sock
                    if target:
                        try:
                            target.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass

        # A socket timeout measures inactivity; the timer also bounds continuous fragments.
        timer = threading.Timer(settings['timeout'], expire)
        timer.daemon = True
        timer.start()
        try:
            if cancel_event.is_set():
                raise Cancelled()
            payload = {'model': model, 'prompt': settings['prompt'], 'stream': True, 'think': settings['think'], 'keep_alive': '2m', 'options': {'num_ctx': settings['num_ctx'], 'num_predict': settings['num_predict'], 'temperature': 0, 'seed': 42}}
            conn.request('POST', '/api/generate', body=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with self._lock:
                self._socket = conn.sock
                active_socket = conn.sock
            if cancel_event.is_set():
                raise Cancelled()
            if expired.is_set() or time.perf_counter() >= deadline:
                raise TimeoutError('Tempo máximo da execução excedido.')
            response = conn.getresponse()
            if response.status != 200:
                detail = response.read(2000).decode('utf-8', 'replace')
                raise ValueError(f'Ollama HTTP {response.status}: {detail}')
            while True:
                if cancel_event.is_set():
                    raise Cancelled()
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    raise TimeoutError('Tempo máximo da execução excedido.')
                if active_socket:
                    active_socket.settimeout(remaining)
                line = response.readline(1024 * 1024 + 1)
                if expired.is_set() or time.perf_counter() >= deadline:
                    raise TimeoutError('Tempo máximo da execução excedido.')
                if not line:
                    break
                if len(line) > 1024 * 1024:
                    raise ValueError('Fragmento do Ollama excedeu 1 MiB.')
                chunk = json.loads(line)
                if chunk.get('error'):
                    raise ValueError(str(chunk['error']))
                elapsed = time.perf_counter() - started
                output, thinking = chunk.get('response', ''), chunk.get('thinking', '')
                if first_content is None and (output or thinking):
                    first_content = elapsed
                if first_text is None and output:
                    first_text = elapsed
                if isinstance(output, str):
                    text = (text + output)[:64000]
                if chunk.get('done'):
                    final = chunk
                    break
            if cancel_event.is_set():
                raise Cancelled()
            elapsed = time.perf_counter() - started
            if expired.is_set() or elapsed >= settings['timeout']:
                raise TimeoutError('Tempo máximo da execução excedido.')
            if final is None:
                raise ValueError('Stream interrompido sem métricas finais.')
            result = metrics(final, elapsed, first_content, first_text)
            result['response'] = text
            return result
        except Exception:
            if cancel_event.is_set():
                raise Cancelled() from None
            if expired.is_set():
                raise TimeoutError('Tempo máximo da execução excedido.') from None
            raise
        finally:
            timer.cancel()
            if response is not None:
                response.close()
            conn.close()
            with self._lock:
                if self._active is conn:
                    self._active = None
                    self._socket = None
