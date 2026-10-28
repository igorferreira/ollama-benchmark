"""Unit and local HTTP integration tests. No Ollama or external packages required."""
import csv
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

from backend.exports import csv_export
from backend.http import AppServer
from backend.manager import BenchmarkManager
from backend.metrics import metrics, summarize
from backend.ollama import Cancelled, OllamaClient
from backend.validation import validate_settings

SETTINGS = {'models': ['test:small'], 'prompt': 'Explique APIs.', 'num_predict': 8, 'num_ctx': 512, 'repetitions': 2, 'timeout': 10, 'think': False}
FINAL = {'done': True, 'eval_count': 8, 'eval_duration': 2_000_000_000, 'load_duration': 100_000_000, 'prompt_eval_count': 4, 'prompt_eval_duration': 200_000_000, 'total_duration': 2_300_000_000, 'done_reason': 'length'}


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        data = {'models': [{'name': 'test:small', 'size': 1000, 'size_vram': 800}]}
        encoded = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.requests.append(payload)
        self.send_response(200)
        self.end_headers()
        self.server.started.set()
        if self.server.mode == 'slow':
            self.server.release.wait(4)
        chunks = [{'thinking': 'pensando'}, {'response': 'Olá '}, {'response': 'mundo!'}, FINAL]
        if self.server.mode == 'error':
            chunks = [{'error': 'modelo inválido'}]
        elif self.server.mode == 'incomplete':
            chunks = [{'response': 'incompleto'}]
        try:
            if self.server.mode == 'trickle':
                for byte in json.dumps(FINAL).encode() + b'\n':
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                    time.sleep(.01)
                return
            for chunk in chunks:
                data = json.dumps(chunk, ensure_ascii=False).encode() + b'\n'
                # Fragment each JSON line and split multibyte UTF-8 across writes.
                for offset in range(0, len(data), 3):
                    self.wfile.write(data[offset:offset+3])
                    self.wfile.flush()
                time.sleep(.005)
        except (BrokenPipeError, ConnectionResetError):
            pass


class HttpFixture(unittest.TestCase):
    def setUp(self):
        self.ollama = ThreadingHTTPServer(('127.0.0.1', 0), FakeOllama)
        self.ollama.daemon_threads = True
        self.ollama.requests = []
        self.ollama.mode = 'normal'
        self.ollama.started = threading.Event()
        self.ollama.release = threading.Event()
        self.thread = threading.Thread(target=self.ollama.serve_forever, daemon=True)
        self.thread.start()
        self.client = OllamaClient(f'http://127.0.0.1:{self.ollama.server_port}')

    def tearDown(self):
        self.ollama.release.set()
        self.ollama.shutdown()
        self.ollama.server_close()
        self.thread.join(2)


class CalculationTests(unittest.TestCase):
    def test_metrics_and_units(self):
        result = metrics(FINAL, 3, .1, .2)
        self.assertEqual(result['tokens_per_s'], 4)
        self.assertEqual(result['load_s'], .1)
        self.assertEqual(result['first_text_s'], .2)
        self.assertEqual(result['total_s'], 2.3)

    def test_zero_and_missing_durations_are_not_infinite(self):
        self.assertIsNone(metrics({**FINAL, 'eval_duration': 0}, 1, None, None)['tokens_per_s'])
        self.assertIsNone(metrics({'eval_count': 2}, 1, None, None)['load_s'])

    def test_missing_tokens_rejected(self):
        with self.assertRaises(ValueError):
            metrics({}, 1, None, None)

    def test_validation_and_deduplication(self):
        self.assertEqual(validate_settings({**SETTINGS, 'models': ['x', 'x']})['models'], ['x'])
        for change in [{'num_predict': 0}, {'repetitions': True}, {'models': []}, {'prompt': ''}, {'think': 'false'}, {'timeout': 1801}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_settings({**SETTINGS, **change})

    def test_destination_restrictions(self):
        for url in ['https://localhost:11434', 'http://example.com', 'http://user@localhost', 'http://localhost/path', 'http://localhost?x=1']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                OllamaClient(url)
        OllamaClient('http://host.docker.internal:11434')

    def test_summary_excludes_initial_and_failed_rows(self):
        rows = [{'model': 'x', 'run': run, 'status': 'completed', 'tokens_per_s': speed} for run, speed in [(1, 1), (2, 4), (3, 6)]]
        rows.append({'model': 'x', 'run': 4, 'status': 'failed'})
        summary = summarize(rows)[0]
        self.assertEqual(summary['tokens_per_s'], 5)
        self.assertEqual(summary['repeated_count'], 2)
        self.assertEqual(summary['initial']['tokens_per_s'], 1)

    def test_csv_handles_quotes_newlines_and_formulas(self):
        state = {'rows': [{'model': '=formula', 'status': 'completed', 'tokens': 8}], 'settings': {**SETTINGS, 'prompt': 'texto, com "aspas"\ne quebra'}, 'started_at': 'today'}
        exported = csv_export(state)
        rows = list(csv.DictReader(io.StringIO(exported.lstrip('\ufeff'))))
        self.assertEqual(rows[0]['model'], "'=formula")
        self.assertEqual(rows[0]['prompt'], state['settings']['prompt'])


class ClientTests(HttpFixture):
    def test_fragmented_utf8_stream_and_thinking(self):
        result = self.client.generate('test:small', SETTINGS, threading.Event())
        self.assertEqual(result['response'], 'Olá mundo!')
        self.assertLess(result['first_content_s'], result['first_text_s'])
        self.assertEqual(result['tokens'], 8)
        self.assertEqual(result['tokens_per_s'], 4)
        self.assertEqual(self.ollama.requests[0]['options']['num_predict'], 8)
        self.assertFalse(self.ollama.requests[0]['think'])

    def test_stream_error(self):
        self.ollama.mode = 'error'
        with self.assertRaisesRegex(ValueError, 'modelo inválido'):
            self.client.generate('test:small', SETTINGS, threading.Event())

    def test_incomplete_stream(self):
        self.ollama.mode = 'incomplete'
        with self.assertRaisesRegex(ValueError, 'sem métricas'):
            self.client.generate('test:small', SETTINGS, threading.Event())

    def test_cancel_unblocks_current_request(self):
        self.ollama.mode = 'slow'
        event = threading.Event()
        errors = []
        def run():
            try:
                self.client.generate('test:small', SETTINGS, event)
            except Exception as exc:
                errors.append(exc)
        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        self.assertTrue(self.ollama.started.wait(2))
        event.set()
        self.client.cancel()
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertIsInstance(errors[0], Cancelled)

    def test_timeout(self):
        self.ollama.mode = 'slow'
        with self.assertRaises(TimeoutError):
            self.client.generate('test:small', {**SETTINGS, 'timeout': .03}, threading.Event())

    def test_continuous_fragments_obey_total_deadline(self):
        self.ollama.mode = 'trickle'
        started = time.perf_counter()
        with self.assertRaisesRegex(TimeoutError, 'Tempo máximo'):
            self.client.generate('test:small', {**SETTINGS, 'timeout': .08}, threading.Event())
        self.assertLess(time.perf_counter() - started, .8)

    def test_terminal_state_published_with_current_cleared(self):
        manager = BenchmarkManager(self.client)
        observations = []
        class ObservedLock:
            def __init__(self):
                self.lock = threading.Lock()
            def __enter__(self):
                self.lock.acquire()
            def __exit__(self, *_args):
                observations.append((manager.state['status'], manager.state['current']))
                self.lock.release()
        manager.lock = ObservedLock()
        manager.start(SETTINGS)
        manager.thread.join(3)
        terminal = [current for status, current in observations if status == 'completed']
        self.assertTrue(terminal)
        self.assertTrue(all(current is None for current in terminal))

    def test_manager_sequential_execution_and_busy_rejection(self):
        self.ollama.mode = 'slow'
        manager = BenchmarkManager(self.client)
        manager.start(SETTINGS)
        with self.assertRaises(RuntimeError):
            manager.start(SETTINGS)
        self.ollama.release.set()
        manager.thread.join(3)
        state = manager.snapshot()
        self.assertEqual(state['status'], 'completed')
        self.assertEqual(len(state['rows']), 2)
        self.assertEqual([r['run'] for r in state['rows']], [1, 2])
        self.assertEqual(state['summary'][0]['repeated_count'], 1)
        self.assertTrue(state['rows'][0]['loaded_before'])

    def test_missing_model_fails_without_download(self):
        manager = BenchmarkManager(self.client)
        manager.start({**SETTINGS, 'models': ['absent']})
        manager.thread.join(2)
        self.assertEqual(manager.snapshot()['status'], 'failed')
        self.assertEqual(self.ollama.requests, [])

    def test_cancel_prevents_remaining_executions(self):
        self.ollama.mode = 'slow'
        manager = BenchmarkManager(self.client)
        manager.start(SETTINGS)
        self.assertTrue(self.ollama.started.wait(2))
        manager.cancel()
        manager.thread.join(2)
        self.assertEqual(manager.snapshot()['status'], 'cancelled')
        self.assertEqual(len(self.ollama.requests), 1)

    def test_completed_results_survive_later_error(self):
        manager = BenchmarkManager(self.client)
        original = self.client.generate
        calls = []
        def generate(*args):
            calls.append(1)
            if len(calls) == 2:
                raise ValueError('falha posterior')
            return original(*args)
        with patch.object(self.client, 'generate', side_effect=generate):
            manager.start(SETTINGS)
            manager.thread.join(3)
        rows = manager.snapshot()['rows']
        self.assertEqual(rows[0]['status'], 'completed')
        self.assertEqual(rows[0]['tokens'], 8)
        self.assertEqual(rows[1]['status'], 'failed')


class AppTests(HttpFixture):
    def setUp(self):
        super().setUp()
        self.app = AppServer(('127.0.0.1', 0), BenchmarkManager(self.client))
        self.app_thread = threading.Thread(target=self.app.serve_forever, daemon=True)
        self.app_thread.start()
        self.host = f'127.0.0.1:{self.app.server_port}'

    def tearDown(self):
        self.app.manager.cancel()
        if self.app.manager.thread:
            self.app.manager.thread.join(2)
        self.app.shutdown()
        self.app.server_close()
        self.app_thread.join(2)
        super().tearDown()

    def call(self, path='/', method='GET', value=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.app.server_port, timeout=3)
        merged = {'Host': self.host, **(headers or {})}
        body = json.dumps(value).encode() if value is not None else None
        if body is not None:
            merged.setdefault('Content-Type', 'application/json')
            merged.setdefault('X-Benchmark-Token', self.app.token)
        conn.request(method, path, body=body, headers=merged)
        response = conn.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        conn.close()
        return result

    def test_page_assets_and_token(self):
        status, headers, body = self.call()
        self.assertEqual(status, 200)
        self.assertIn(self.app.token.encode(), body)
        self.assertIn(b'id="theme-select"', body)
        self.assertLess(body.index(b'<script src="/app.js">'), body.index(b'<link rel="stylesheet"'))
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        for path in ['/app.js', '/style.css', '/api/health', '/api/models']:
            self.assertEqual(self.call(path)[0], 200)

    def test_host_and_origin_rejected(self):
        self.assertEqual(self.call(headers={'Host': 'evil.example'})[0], 403)
        self.assertEqual(self.call(headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.call(headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)

    def test_post_requires_token(self):
        self.assertEqual(self.call('/api/start', 'POST', SETTINGS, {'X-Benchmark-Token': 'bad'})[0], 403)

    def test_invalid_input_and_body_size(self):
        self.assertEqual(self.call('/api/start', 'POST', {**SETTINGS, 'num_ctx': -1})[0], 400)
        self.assertEqual(self.call('/api/start', 'POST', SETTINGS, {'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.call('/api/start', 'POST', SETTINGS, {'Content-Length': '70000'})[0], 413)

    def test_ollama_offline_returns_clear_error(self):
        with patch.object(self.client, 'get', side_effect=ConnectionRefusedError('connection refused')):
            status, _headers, body = self.call('/api/models')
        self.assertEqual(status, 502)
        self.assertIn('Ollama local', json.loads(body)['error'])

    def test_end_to_end_job_and_exports(self):
        self.assertEqual(self.call('/api/start', 'POST', SETTINGS)[0], 202)
        self.app.manager.thread.join(3)
        state = json.loads(self.call('/api/state')[2])
        self.assertEqual(state['status'], 'completed')
        self.assertEqual(len(state['rows']), 2)
        csv_status, headers, csv_body = self.call('/api/export?format=csv')
        self.assertEqual(csv_status, 200)
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertEqual(len(list(csv.DictReader(io.StringIO(csv_body.decode('utf-8-sig'))))), 2)
        json_state = json.loads(self.call('/api/export?format=json')[2])
        self.assertEqual(json_state['settings']['prompt'], SETTINGS['prompt'])


class CliTests(unittest.TestCase):
    def test_cli_starts_composition_root_without_ollama(self):
        root = Path(__file__).resolve().parent.parent
        environment = {**os.environ, 'APP_BIND': '127.0.0.1', 'APP_PORT': '8765', 'OLLAMA_URL': 'http://127.0.0.1:9'}
        process = subprocess.Popen(
            [sys.executable, str(root / 'app.py'), '--no-browser', '--port', '0'],
            cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8',
        )
        lines = Queue()
        reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
        reader.start()
        connection = None
        try:
            line = lines.get(timeout=5).strip()
            self.assertTrue(line.startswith('Ollama Benchmark: http://127.0.0.1:'), line)
            port = int(line.rsplit(':', 1)[1])
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            for endpoint in ['/api/health', '/app.js']:
                connection.request('GET', endpoint)
                with connection.getresponse() as response:
                    self.assertEqual(response.status, 200)
                    body = response.read()
                    if endpoint == '/api/health':
                        self.assertEqual(json.loads(body), {'status': 'ok'})
                    else:
                        self.assertIn(b'DOMContentLoaded', body)
        finally:
            if connection is not None:
                connection.close()
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            reader.join(timeout=1)
            process.stdout.close()


if __name__ == '__main__':
    unittest.main()
