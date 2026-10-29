"""Sequential benchmark jobs and shared in-memory state."""
from __future__ import annotations

import copy
import threading
import time
from datetime import datetime, timezone

from .metrics import summarize, usage
from .ollama import Cancelled
from .validation import validate_settings


class BenchmarkManager:
    def __init__(self, client):
        self.client = client
        self.lock = threading.Lock()
        self.cancel_event = threading.Event()
        self.thread = None
        self._live_started = None
        self.state = {'status': 'idle', 'rows': [], 'settings': None, 'current': None, 'started_at': None, 'error': None, 'live': None}

    def snapshot(self):
        with self.lock:
            result = copy.deepcopy(self.state)
            if result['live'] is not None and self._live_started is not None:
                result['live']['elapsed_s'] = max(0, time.perf_counter() - self._live_started)
        result['usage'] = usage(result['rows'])
        result['summary'] = summarize(result['rows'])
        return result

    def is_active(self):
        with self.lock:
            return self.state['status'] in {'running', 'cancelling'}

    def start(self, value):
        settings = validate_settings(value)
        with self.lock:
            if self.state['status'] in {'running', 'cancelling'}:
                raise RuntimeError('Já existe um teste em andamento.')
            self.cancel_event = threading.Event()
            self._live_started = None
            self.state = {'status': 'running', 'settings': settings, 'rows': [], 'current': None, 'started_at': datetime.now(timezone.utc).isoformat(), 'error': None, 'live': None}
            self.thread = threading.Thread(target=self._run, args=(settings,), daemon=True)
            self.thread.start()

    def cancel(self):
        with self.lock:
            if self.state['status'] not in {'running', 'cancelling'}:
                return
            self.state['status'] = 'cancelling'
            self.cancel_event.set()
        self.client.cancel()

    def _publish_live(self, event):
        with self.lock:
            self.state['live'].update(event)
            self._live_started = time.perf_counter() - event['elapsed_s'] if event['status'] in {'waiting', 'streaming'} else None

    def _finish_live(self, status, row=None):
        with self.lock:
            live = self.state['live']
            if self._live_started is not None:
                live['elapsed_s'] = max(0, time.perf_counter() - self._live_started)
            self._live_started = None
            live['status'] = status
            if row is not None:
                live.update({field: row.get(field) for field in ['tokens', 'prompt_tokens', 'prompt_cached_tokens', 'total_tokens', 'output_tokens_observed', 'token_observation_status']})
                live.update(response=row.get('response', ''), elapsed_s=row['wall_s'], count_status='final')
            else:
                live.update(tokens=None, prompt_tokens=None, prompt_cached_tokens=None, total_tokens=None, count_status='unavailable', output_tokens_observed=None, token_observation_status='unavailable' if self.state['settings']['live_token_count'] else 'disabled')

    def _run(self, settings):
        terminal_status, terminal_error = 'completed', None
        try:
            installed = {m['name'] for m in self.client.get('/api/tags').get('models', [])}
            if any(model not in installed for model in settings['models']):
                raise ValueError('Um modelo selecionado não está instalado. Atualize a lista.')
            for model in settings['models']:
                for run in range(1, settings['repetitions'] + 1):
                    if self.cancel_event.is_set():
                        raise Cancelled()
                    row = {'model': model, 'run': run, 'phase': 'initial' if run == 1 else 'repeated', 'status': 'failed', 'output_tokens_observed': None, 'token_observation_status': 'unavailable' if settings['live_token_count'] else 'disabled'}
                    with self.lock:
                        self.state['current'] = {'model': model, 'run': run}
                        self._live_started = None
                        self.state['live'] = {
                            'model': model, 'run': run, 'status': 'waiting', 'elapsed_s': 0,
                            'response': '', 'output_characters': 0, 'thinking_characters': 0, 'fragments': 0,
                            'first_content_s': None, 'first_text_s': None, 'tokens': None, 'prompt_tokens': None,
                            'prompt_cached_tokens': None, 'total_tokens': None, 'count_status': 'pending',
                            'output_tokens_observed': 0 if settings['live_token_count'] else None,
                            'token_observation_status': 'pending' if settings['live_token_count'] else 'disabled',
                        }
                    try:
                        loaded = self.client.get('/api/ps').get('models', [])
                        row['loaded_before'] = any(m.get('name') == model or m.get('model') == model for m in loaded)
                        row.update(self.client.generate(model, settings, self.cancel_event, progress=self._publish_live))
                        row['status'] = 'completed'
                        self._finish_live('completed', row)
                        try:
                            info = next((m for m in self.client.get('/api/ps').get('models', []) if m.get('name') == model or m.get('model') == model), {})
                            row['size_vram'] = info.get('size_vram')
                            row['size_memory'] = info.get('size')
                        except Exception as exc:
                            row['warning'] = 'Memória após o teste indisponível: ' + str(exc)
                    except Cancelled:
                        row['status'] = 'cancelled'
                        self._finish_live('cancelled')
                        with self.lock:
                            self.state['rows'].append(row)
                        raise
                    except Exception as exc:
                        row['error'] = str(exc)
                        self._finish_live('failed')
                    with self.lock:
                        self.state['rows'].append(row)
            terminal_status = 'completed'
        except Cancelled:
            terminal_status = 'cancelled'
        except Exception as exc:
            terminal_status, terminal_error = 'failed', str(exc)
        finally:
            with self.lock:
                self.state['status'] = 'cancelled' if self.cancel_event.is_set() else terminal_status
                self.state['error'] = terminal_error
                self.state['current'] = None
