"""Bounded, local terminal comparison storage; never accepts user supplied paths."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
import uuid

from .exports import CSV_FIELDS
from .metrics import summarize
from .validation import validate_settings

MAX_BYTES = 64 * 1024 * 1024
WARNING = 'Alguns históricos estão indisponíveis ou não puderam ser salvos.'
TERMINAL = {'completed', 'failed', 'cancelled'}


def validate_id(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{32}', value) is None:
        raise ValueError('Identificador de histórico inválido.')
    return value


def terminal_state(value):
    """Validate and project only benchmark data, excluding runtime/session inventory."""
    if not isinstance(value, dict) or value.get('status') not in TERMINAL:
        raise ValueError('Histórico inválido.')
    settings = validate_settings(value.get('settings'))
    rows = value.get('rows')
    if not isinstance(rows, list) or len(rows) > 200:
        raise ValueError('Histórico inválido.')
    clean_rows = []
    for row in rows:
        if not isinstance(row, dict) or row.get('status') not in TERMINAL or row.get('model') not in settings['models'] or type(row.get('run')) is not int or not 1 <= row['run'] <= settings['repetitions']:
            raise ValueError('Histórico inválido.')
        clean = {}
        for key in CSV_FIELDS + ['response', 'warning']:
            if key in row:
                field = row[key]
                if field is not None and not isinstance(field, (str, int, float, bool)):
                    raise ValueError('Histórico inválido.')
                if isinstance(field, float) and not math.isfinite(field):
                    raise ValueError('Histórico inválido.')
                if isinstance(field, str) and len(field) > (64000 if key == 'response' else 16000):
                    raise ValueError('Histórico inválido.')
                text_fields = {'model', 'phase', 'status', 'done_reason', 'error', 'response', 'warning', 'token_observation_status'}
                if key in text_fields and field is not None and not isinstance(field, str):
                    raise ValueError('Histórico inválido.')
                if key not in text_fields and key != 'loaded_before' and field is not None and (isinstance(field, bool) or not isinstance(field, (int, float)) or field < 0):
                    raise ValueError('Histórico inválido.')
                if key == 'loaded_before' and field is not None and type(field) is not bool:
                    raise ValueError('Histórico inválido.')
                clean[key] = field
        clean_rows.append(clean)
    started = value.get('started_at')
    error = value.get('error')
    if started is not None and (not isinstance(started, str) or len(started) > 100):
        raise ValueError('Histórico inválido.')
    if error is not None and (not isinstance(error, str) or len(error) > 16000):
        raise ValueError('Histórico inválido.')
    return {'status': value['status'], 'settings': settings, 'rows': clean_rows,
            'current': None, 'started_at': started, 'error': error, 'live': None}


class HistoryRepository:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else Path.home() / '.ollama_benchmark'
        self.lock = threading.Lock()

    def _prepare(self):
        if self.root.is_symlink():
            raise OSError('Armazenamento indisponível.')
        self.root.mkdir(mode=0o700, parents=False, exist_ok=True)
        if not self.root.is_dir() or self.root.is_symlink():
            raise OSError('Armazenamento indisponível.')
        if os.name != 'nt':
            self.root.chmod(0o700)

    def save(self, state):
        identifier = uuid.uuid4().hex
        saved_at = datetime.now(timezone.utc).isoformat()
        metadata = {'id': identifier, 'saved_at': saved_at, 'saved': False, 'warning': WARNING, 'enabled': True}
        temporary = None
        try:
            envelope = {'version': 1, 'id': identifier, 'saved_at': saved_at, 'state': terminal_state(state)}
            encoded = json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode('utf-8')
            if len(encoded) > MAX_BYTES:
                raise ValueError('Histórico muito grande.')
            with self.lock:
                self._prepare()
                fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=self.root)
                with os.fdopen(fd, 'wb') as output:
                    if os.name != 'nt':
                        os.fchmod(output.fileno(), 0o600)
                    output.write(encoded)
                    output.flush()
                    os.fsync(output.fileno())
                destination = self.root / (identifier + '.json')
                if destination.exists() or destination.is_symlink():
                    raise OSError('Histórico indisponível.')
                os.replace(temporary, destination)
                temporary = None
            metadata.update(saved=True, warning=None)
        except (OSError, ValueError, TypeError):
            metadata.update(id=None, saved_at=None)
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
        return metadata

    def _load(self, identifier):
        validate_id(identifier)
        if self.root.is_symlink():
            raise FileNotFoundError('Histórico indisponível.')
        path = self.root / (identifier + '.json')
        if path.is_symlink():
            raise FileNotFoundError('Histórico indisponível.')
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, 'rb') as source:
            details = os.fstat(source.fileno())
            if not stat.S_ISREG(details.st_mode) or details.st_size > MAX_BYTES:
                raise ValueError('Histórico inválido.')
            content = source.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError('Histórico inválido.')
        envelope = json.loads(content, parse_constant=lambda _value: (_ for _ in ()).throw(ValueError('Histórico inválido.')))
        if not isinstance(envelope, dict) or type(envelope.get('version')) is not int or envelope['version'] != 1 or envelope.get('id') != identifier:
            raise ValueError('Histórico inválido.')
        saved_at = envelope.get('saved_at')
        if not isinstance(saved_at, str) or len(saved_at) > 100:
            raise ValueError('Histórico inválido.')
        parsed = datetime.fromisoformat(saved_at)
        if parsed.tzinfo is None:
            raise ValueError('Histórico inválido.')
        return {'version': 1, 'id': identifier, 'saved_at': parsed.astimezone(timezone.utc).isoformat(), 'state': terminal_state(envelope.get('state'))}

    def load(self, identifier):
        validate_id(identifier)
        try:
            with self.lock:
                return self._load(identifier)
        except (OSError, ValueError, TypeError, OverflowError, RecursionError):
            raise FileNotFoundError('Histórico indisponível ou inválido.') from None

    def _scan(self, latest=False):
        items, best, warning = [], None, None
        try:
            if self.root.is_symlink():
                raise OSError()
            if not self.root.exists():
                return (None if latest else []), None
            for path in self.root.iterdir():
                if path.suffix != '.json':
                    continue
                try:
                    item = self._load(validate_id(path.stem))
                    if latest:
                        if best is None or (item['saved_at'], item['id']) > (best['saved_at'], best['id']):
                            best = item
                    else:
                        state = item['state']
                        summaries = {summary['model']: summary for summary in summarize(state['rows'])}
                        projected = []
                        for model in state['settings']['models']:
                            summary = summaries.get(model, {})
                            projected.append({'model': model, 'repeated_count': summary.get('repeated_count', 0),
                                              'tokens_per_s': summary.get('tokens_per_s'),
                                              'first_text_s': summary.get('first_text_s'),
                                              'wall_s': summary.get('wall_s'),
                                              'initial_wall_s': (summary.get('initial') or {}).get('wall_s')})
                        items.append({'id': item['id'], 'saved_at': item['saved_at'], 'status': state['status'],
                                      'models': state['settings']['models'], 'started_at': state['started_at'],
                                      'runs': len(state['rows']), 'summary': projected})
                    # Do not retain response bodies from every comparison while scanning.
                    del item
                except (OSError, ValueError, TypeError, OverflowError, RecursionError):
                    warning = WARNING
        except OSError:
            warning = WARNING
        if latest:
            return best, warning
        items.sort(key=lambda item: (item['saved_at'], item['id']), reverse=True)
        return items, warning

    def list(self):
        with self.lock:
            items, warning = self._scan()
        return {'enabled': True, 'warning': warning, 'items': items}

    def latest(self):
        with self.lock:
            try:
                self._prepare()
            except OSError:
                return None, WARNING
            return self._scan(latest=True)
