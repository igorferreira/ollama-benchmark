"""Sequential benchmark jobs and shared in-memory state."""
from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone

from .metrics import summarize
from .ollama import Cancelled
from .validation import validate_settings


class BenchmarkManager:
    def __init__(self, client):
        self.client = client
        self.lock = threading.Lock()
        self.cancel_event = threading.Event()
        self.thread = None
        self.state = {'status': 'idle', 'rows': [], 'settings': None, 'current': None, 'started_at': None, 'error': None}

    def snapshot(self):
        with self.lock:
            result = copy.deepcopy(self.state)
        result['summary'] = summarize(result['rows'])
        return result

    def start(self, value):
        settings = validate_settings(value)
        with self.lock:
            if self.state['status'] in {'running', 'cancelling'}:
                raise RuntimeError('Já existe um teste em andamento.')
            self.cancel_event = threading.Event()
            self.state = {'status': 'running', 'settings': settings, 'rows': [], 'current': None, 'started_at': datetime.now(timezone.utc).isoformat(), 'error': None}
            self.thread = threading.Thread(target=self._run, args=(settings,), daemon=True)
            self.thread.start()

    def cancel(self):
        with self.lock:
            if self.state['status'] not in {'running', 'cancelling'}:
                return
            self.state['status'] = 'cancelling'
            self.cancel_event.set()
        self.client.cancel()

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
                    row = {'model': model, 'run': run, 'phase': 'initial' if run == 1 else 'repeated', 'status': 'failed'}
                    with self.lock:
                        self.state['current'] = {'model': model, 'run': run}
                    try:
                        loaded = self.client.get('/api/ps').get('models', [])
                        row['loaded_before'] = any(m.get('name') == model or m.get('model') == model for m in loaded)
                        row.update(self.client.generate(model, settings, self.cancel_event))
                        row['status'] = 'completed'
                        try:
                            info = next((m for m in self.client.get('/api/ps').get('models', []) if m.get('name') == model or m.get('model') == model), {})
                            row['size_vram'] = info.get('size_vram')
                            row['size_memory'] = info.get('size')
                        except Exception as exc:
                            row['warning'] = 'Memória após o teste indisponível: ' + str(exc)
                    except Cancelled:
                        row['status'] = 'cancelled'
                        with self.lock:
                            self.state['rows'].append(row)
                        raise
                    except Exception as exc:
                        row['error'] = str(exc)
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
