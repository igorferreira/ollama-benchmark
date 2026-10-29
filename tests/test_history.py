"""History tests use synthetic snapshots and temporary directories only."""
import copy
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from backend.history import HistoryRepository, MAX_BYTES
from backend.http import AppServer
from backend.manager import BenchmarkManager

SETTINGS = {'models': ['fixture'], 'prompt': 'Olá sintético', 'repetitions': 2}
STATE = {'status': 'completed', 'settings': SETTINGS, 'rows': [{'model': 'fixture', 'run': 1, 'phase': 'initial', 'status': 'completed', 'tokens': 2, 'response': 'Resposta', 'wall_s': 1}], 'started_at': '2026-01-01T00:00:00+00:00', 'error': None}


class Client:
    def get(self, _path):
        return {'models': [{'name': 'fixture'}]}

    def generate(self, *_args, **_kwargs):
        return {'tokens': 2, 'response': 'Resposta', 'wall_s': 1}

    def cancel(self):
        pass


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'history'
        self.repository = HistoryRepository(self.root)

    def test_multiple_snapshots_restore_latest_and_utf8(self):
        first = self.repository.save(STATE)
        second = self.repository.save({**STATE, 'status': 'cancelled'})
        self.assertTrue(first['saved'])
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(len(self.repository.list()['items']), 2)
        latest, warning = self.repository.latest()
        self.assertIsNone(warning)
        self.assertEqual(latest['id'], second['id'])
        manager = BenchmarkManager(Client(), self.repository)
        self.assertEqual(manager.snapshot()['status'], 'cancelled')
        self.assertEqual(manager.snapshot()['settings']['prompt'], 'Olá sintético')

    def test_list_projects_separate_model_summaries_without_prompt_or_response(self):
        state = copy.deepcopy(STATE)
        state['settings']['models'].append('missing')
        state['rows'][0]['response'] = 'PRIVATE_RESPONSE_SENTINEL'
        state['settings']['prompt'] = 'PRIVATE_PROMPT_SENTINEL'
        state['rows'].append({**state['rows'][0], 'run': 2, 'wall_s': 3, 'first_text_s': .4, 'tokens_per_s': 7})
        first = self.repository.save(state)
        second = self.repository.save({**state, 'started_at': '2026-01-02T00:00:00+00:00', 'status': 'failed', 'rows': []})
        items = self.repository.list()['items']
        self.assertEqual([item['id'] for item in items], [second['id'], first['id']])
        self.assertEqual([item['started_at'] for item in items], ['2026-01-02T00:00:00+00:00', STATE['started_at']])
        self.assertEqual(items[1]['summary'], [
            {'model': 'fixture', 'repeated_count': 1, 'tokens_per_s': 7, 'first_text_s': .4, 'wall_s': 3, 'initial_wall_s': 1},
            {'model': 'missing', 'repeated_count': 0, 'tokens_per_s': None, 'first_text_s': None, 'wall_s': None, 'initial_wall_s': None},
        ])
        for summary in items[0]['summary']:
            self.assertEqual(summary['repeated_count'], 0)
            self.assertIsNone(summary['wall_s'])
        encoded = json.dumps(items)
        self.assertNotIn('PRIVATE_RESPONSE_SENTINEL', encoded)
        self.assertNotIn('PRIVATE_PROMPT_SENTINEL', encoded)
        self.assertNotIn('initial"', encoded)

    def test_startup_creates_private_folder_and_io_failure_is_nonfatal(self):
        self.assertFalse(self.root.exists())
        manager = BenchmarkManager(Client(), self.repository)
        self.assertTrue(self.root.is_dir())
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(manager.snapshot()['status'], 'idle')
        if os.name != 'nt':
            self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        with patch.object(self.repository, '_prepare', side_effect=OSError('/private/path secret')):
            failed = BenchmarkManager(Client(), self.repository).snapshot()
        self.assertEqual(failed['status'], 'idle')
        self.assertIsNotNone(failed['history']['warning'])
        self.assertNotIn('secret', str(failed))
        self.assertNotIn('/private/path', str(failed))

    def test_permissions_atomic_and_no_temporary_left(self):
        with patch('backend.history.os.replace', wraps=os.replace) as replace:
            result = self.repository.save(STATE)
        self.assertTrue(result['saved'])
        self.assertEqual(replace.call_count, 1)
        self.assertEqual(len(list(self.root.iterdir())), 1)
        if os.name != 'nt':
            self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
            self.assertEqual(next(self.root.iterdir()).stat().st_mode & 0o777, 0o600)

    def test_storage_failure_is_nonfatal_and_generic(self):
        with patch('backend.history.os.replace', side_effect=OSError('/private/path secret')):
            result = self.repository.save(STATE)
        self.assertFalse(result['saved'])
        self.assertNotIn('secret', str(result))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_projection_excludes_session_inventory_and_unknown_nested_fields(self):
        state = copy.deepcopy(STATE)
        state.update(token='secret-session', system={'hostname': 'private-host'}, history={'token': 'private'})
        state['settings']['password'] = 'not-saved'
        state['rows'][0]['system'] = {'hostname': 'not-saved'}
        result = self.repository.save(state)
        content = (self.root / (result['id'] + '.json')).read_text()
        for forbidden in ['secret-session', 'private-host', 'not-saved', 'hostname', 'password']:
            self.assertNotIn(forbidden, content)

    def test_corrupt_invalid_nonterminal_and_nonfinite_are_ignored(self):
        valid = self.repository.save(STATE)
        (self.root / ('a' * 32 + '.json')).write_text('{bad')
        (self.root / ('b' * 32 + '.json')).write_text(json.dumps({'version': 1, 'id': 'b' * 32, 'saved_at': 'date', 'state': STATE}))
        listing = self.repository.list()
        self.assertEqual([item['id'] for item in listing['items']], [valid['id']])
        self.assertIsNotNone(listing['warning'])
        for state in [{**STATE, 'status': 'running'}, {**STATE, 'rows': [{**STATE['rows'][0], 'tokens': float('nan')}]}, {**STATE, 'rows': [{**STATE['rows'][0], 'wall_s': 'bad'}]}]:
            self.assertFalse(self.repository.save(state)['saved'])

    def test_ids_and_symlinks_do_not_escape_directory(self):
        for invalid in ['../outside', 'a' * 31, 'A' * 32, None, []]:
            with self.assertRaises(ValueError):
                self.repository.load(invalid)
        outside = Path(self.temp.name) / 'outside'
        outside.write_text('private')
        self.root.mkdir()
        try:
            (self.root / ('a' * 32 + '.json')).symlink_to(outside)
        except OSError:
            self.skipTest('Symlinks indisponíveis nesta plataforma.')
        with self.assertRaises(FileNotFoundError):
            self.repository.load('a' * 32)
        self.assertEqual(outside.read_text(), 'private')
        linked = Path(self.temp.name) / 'linked'
        linked.symlink_to(self.root, target_is_directory=True)
        self.assertFalse(HistoryRepository(linked).save(STATE)['saved'])

    def test_oversize_file_is_rejected_before_json_parsing(self):
        self.root.mkdir()
        path = self.root / ('c' * 32 + '.json')
        with path.open('wb') as output:
            output.truncate(MAX_BYTES + 1)
        with patch('backend.history.json.loads') as loads:
            with self.assertRaises(FileNotFoundError):
                self.repository.load('c' * 32)
            loads.assert_not_called()

    def test_manager_saves_once_outside_lock_and_restores_without_generation(self):
        manager = BenchmarkManager(Client(), self.repository)
        original = self.repository.save
        def save(state):
            self.assertTrue(manager.lock.acquire(blocking=False))
            manager.lock.release()
            return original(state)
        with patch.object(self.repository, 'save', side_effect=save) as call:
            manager.start(SETTINGS)
            manager.thread.join(3)
        self.assertEqual(call.call_count, 1)
        self.assertTrue(manager.snapshot()['history']['saved'])
        self.assertEqual(len(manager.snapshot()['rows']), 2)
        restored = manager.load_history(manager.snapshot()['history']['id'])
        self.assertEqual(restored['status'], 'completed')
        self.assertIsNone(restored['live'])

    def test_failed_and_cancelled_jobs_are_saved_once_without_resume(self):
        from backend.ollama import Cancelled
        for error, status in [(ValueError('Falha sintética'), 'failed'), (Cancelled(), 'cancelled')]:
            client = Client()
            with patch.object(client, 'get', side_effect=error):
                manager = BenchmarkManager(client, self.repository)
                with patch.object(self.repository, 'save', wraps=self.repository.save) as save:
                    manager.start(SETTINGS)
                    manager.thread.join(3)
                self.assertEqual(save.call_count, 1)
                self.assertEqual(manager.snapshot()['status'], status)
                self.assertTrue(manager.snapshot()['history']['saved'])
        self.assertEqual(len(self.repository.list()['items']), 2)

    def test_load_revalidates_after_concurrent_start_without_lock_during_io(self):
        saved = self.repository.save(STATE)
        manager = BenchmarkManager(Client(), self.repository)
        original = self.repository.load
        def load(identifier):
            self.assertTrue(manager.lock.acquire(blocking=False))
            manager._job_id += 1
            manager.lock.release()
            return original(identifier)
        with patch.object(self.repository, 'load', side_effect=load):
            with self.assertRaises(RuntimeError):
                manager.load_history(saved['id'])
        with manager.lock:
            manager.state['status'] = 'running'
        with self.assertRaises(RuntimeError):
            manager.load_history(saved['id'])

    def test_old_save_does_not_overwrite_new_comparison_metadata(self):
        manager = BenchmarkManager(Client(), self.repository)
        def save(_state):
            with manager.lock:
                manager._job_id += 1
                manager.state['history'] = {'new': True}
            return {'old': True}
        with patch.object(self.repository, 'save', side_effect=save):
            manager.start(SETTINGS)
            manager.thread.join(3)
        self.assertEqual(manager.snapshot()['history'], {'new': True})

    def test_http_protections_list_load_and_busy(self):
        saved = self.repository.save(STATE)
        manager = BenchmarkManager(Client(), self.repository)
        server = AppServer(('127.0.0.1', 0), manager)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        def request(method, path, value=None, headers=None):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            body = json.dumps(value) if value is not None else None
            base = {'Content-Type': 'application/json', 'X-Benchmark-Token': server.token}
            base.update(headers or {})
            connection.request(method, path, body=body, headers=base)
            response = connection.getresponse()
            data = json.loads(response.read())
            status, cache = response.status, response.getheader('Cache-Control')
            connection.close()
            return status, cache, data
        status, cache, result = request('GET', '/api/history')
        self.assertEqual((status, cache), (200, 'no-store'))
        self.assertEqual(result['items'][0]['id'], saved['id'])
        self.assertEqual(request('GET', '/api/history', headers={'Host': 'evil.test'})[0], 403)
        self.assertEqual(request('GET', '/api/history', headers={'Origin': 'http://evil.test'})[0], 403)
        self.assertEqual(request('POST', '/api/history/load', {'id': saved['id']}, {'X-Benchmark-Token': 'bad'})[0], 403)
        self.assertEqual(request('POST', '/api/history/load', {'id': '../bad'})[0], 400)
        self.assertEqual(request('POST', '/api/history/load', {'id': 'a' * 32})[0], 404)
        self.assertEqual(request('POST', '/api/history/load', {'id': saved['id']})[0], 200)
        with manager.lock:
            manager.state['status'] = 'cancelling'
        self.assertEqual(request('POST', '/api/history/load', {'id': saved['id']})[0], 409)
