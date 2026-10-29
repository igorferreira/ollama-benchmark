"""Local Ollama HTTP transport and streamed measurements."""
from __future__ import annotations

import http.client
import json
import math
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

    def generate(self, model, settings, cancel_event, progress=None):
        started = time.perf_counter()
        deadline = started + settings['timeout']
        conn = http.client.HTTPConnection(self.host, self.port, timeout=settings['timeout'])
        with self._lock:
            self._active = conn
        first_content = first_text = final = None
        response = None
        text = ''
        expired = threading.Event()
        output_characters = thinking_characters = fragments = 0
        last_published = None
        published_content = False
        observe_tokens = settings.get('live_token_count', False)
        observed_tokens = 0 if observe_tokens else None
        observation_status = 'pending' if observe_tokens else 'disabled'

        def publish(status='waiting', force=False, result=None):
            nonlocal last_published, published_content
            if progress is None:
                return
            now = time.perf_counter()
            first_content_update = fragments > 0 and not published_content
            if not force and not first_content_update and last_published is not None and now - last_published < .25:
                return
            event = {
                'status': status, 'elapsed_s': now - started, 'response': text,
                'output_characters': output_characters, 'thinking_characters': thinking_characters,
                'fragments': fragments, 'first_content_s': first_content, 'first_text_s': first_text,
                'tokens': None, 'prompt_tokens': None, 'prompt_cached_tokens': None, 'total_tokens': None,
                'count_status': 'unavailable' if status in {'failed', 'cancelled'} else 'pending',
                'output_tokens_observed': observed_tokens, 'token_observation_status': observation_status,
            }
            if result is not None:
                event.update({field: result[field] for field in ['tokens', 'prompt_tokens', 'prompt_cached_tokens', 'total_tokens']})
                event['count_status'] = 'final'
                event['elapsed_s'] = result['wall_s']
            elif status in {'failed', 'cancelled'}:
                event.update(output_tokens_observed=None, token_observation_status='unavailable' if observe_tokens else 'disabled')
            progress(event)
            last_published = now
            published_content = published_content or fragments > 0

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
            publish(force=True)
            if cancel_event.is_set():
                raise Cancelled()
            payload = {'model': model, 'prompt': settings['prompt'], 'stream': True, 'think': settings['think'], 'keep_alive': '2m', 'options': {'num_ctx': settings['num_ctx'], 'num_predict': settings['num_predict'], 'temperature': 0, 'seed': 42}}
            if observe_tokens:
                payload.update(logprobs=True, top_logprobs=0)
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
                if observe_tokens and observation_status != 'unavailable':
                    entries = chunk.get('logprobs')
                    if 'logprobs' in chunk or output or thinking:
                        valid = isinstance(entries, list) and (bool(entries) or not (output or thinking)) and all(
                            isinstance(entry, dict) and isinstance(entry.get('token'), str)
                            and (type(entry.get('logprob')) is int or (type(entry.get('logprob')) is float and math.isfinite(entry['logprob'])))
                            for entry in entries
                        )
                        if valid:
                            observed_tokens += len(entries)
                        else:
                            observed_tokens, observation_status = None, 'unavailable'
                if first_content is None and (output or thinking):
                    first_content = elapsed
                if first_text is None and output:
                    first_text = elapsed
                if isinstance(output, str):
                    output_characters += len(output)
                    if len(text) < 64000:
                        text += output[:64000 - len(text)]
                if isinstance(thinking, str):
                    thinking_characters += len(thinking)
                if output or thinking:
                    fragments += 1
                if chunk.get('done'):
                    final = chunk
                    break
                publish('streaming' if fragments else 'waiting')
            if cancel_event.is_set():
                raise Cancelled()
            elapsed = time.perf_counter() - started
            if expired.is_set() or elapsed >= settings['timeout']:
                raise TimeoutError('Tempo máximo da execução excedido.')
            if final is None:
                raise ValueError('Stream interrompido sem métricas finais.')
            result = metrics(final, elapsed, first_content, first_text)
            result['response'] = text
            if observation_status == 'pending':
                observation_status = 'matched' if observed_tokens == result['tokens'] else 'mismatch'
            result.update(output_tokens_observed=observed_tokens, token_observation_status=observation_status)
            publish('completed', force=True, result=result)
            return result
        except Exception:
            publish('cancelled' if cancel_event.is_set() else 'failed', force=True)
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
