"""Authoritative final token counters and bounded live streaming progress."""
import copy
import csv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
from itertools import count
import json
import threading
import time
import unittest
from unittest.mock import patch

from backend.exports import csv_export
from backend.manager import BenchmarkManager
from backend.metrics import metrics, usage
from backend.ollama import OllamaClient
from backend.validation import validate_settings

SETTINGS = {'models': ['live:small'], 'prompt': 'Exemplo fictício', 'num_predict': 128, 'num_ctx': 512, 'repetitions': 2, 'timeout': 10, 'think': False}
FINAL = {'done': True, 'eval_count': 18, 'prompt_eval_count': 11, 'prompt_eval_cached_count': 8, 'eval_duration': 2_000_000_000, 'total_duration': 2_200_000_000, 'load_duration': 0, 'prompt_eval_duration': 100_000_000}


class LiveHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        encoded = json.dumps({'models': [{'name': 'live:small', 'size': 1000, 'size_vram': 800}]}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        self.server.requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        mode = self.server.mode
        if mode == 'unsupported':
            body = b'{"error":"logprobs unsupported"}'
            self.send_response(400)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(200)
        self.end_headers()
        chunks = [{'response': 'Olá'}]
        if mode == 'fast':
            chunks = [{'response': str(number)} for number in range(20)]
        elif mode == 'large':
            chunks = [{'thinking': 'raciocínio que não deve ser armazenado'}, {'response': 'a' * 50000}, {'response': 'b' * 50000}]
        if self.server.chunks is not None:
            chunks = self.server.chunks
        try:
            for chunk in chunks:
                self.wfile.write(json.dumps(chunk, ensure_ascii=False).encode() + b'\n')
                self.wfile.flush()
            self.server.prefix_sent.set()
            if mode == 'blocking':
                self.server.release.wait(4)
            final = {'error': 'falha de geração'} if mode == 'error' else self.server.final
            self.wfile.write(json.dumps(final).encode() + b'\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


class LiveFixture(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), LiveHandler)
        self.server.daemon_threads = True
        self.server.mode = 'normal'
        self.server.chunks = None
        self.server.final = dict(FINAL)
        self.server.requests = []
        self.server.prefix_sent = threading.Event()
        self.server.release = threading.Event()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = OllamaClient(f'http://127.0.0.1:{self.server.server_port}')
        self.manager = None

    def tearDown(self):
        self.server.release.set()
        if self.manager is not None:
            self.manager.cancel()
            self.manager.thread.join(3)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def waiting_snapshot(self):
        self.assertTrue(self.server.prefix_sent.wait(2))
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            value = self.manager.snapshot()
            if value['live'] and value['live']['response']:
                return value
            time.sleep(.005)
        self.fail('Prévia não publicada antes do fragmento final.')


class TokenUsageTests(unittest.TestCase):
    def test_live_count_option_is_strict_and_disabled_by_default(self):
        self.assertFalse(validate_settings(SETTINGS)['live_token_count'])
        self.assertTrue(validate_settings({**SETTINGS, 'live_token_count': True})['live_token_count'])
        for value in [None, 0, 1, 'true']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_settings({**SETTINGS, 'live_token_count': value})

    def test_cache_is_separate_from_input_plus_output(self):
        result = metrics(FINAL, 3, .1, .1)
        self.assertEqual((result['prompt_tokens'], result['tokens'], result['prompt_cached_tokens'], result['total_tokens']), (11, 18, 8, 29))

    def test_missing_invalid_and_zero_counters(self):
        for bad in [None, -1, True, 1.0, '11']:
            with self.subTest(value=bad):
                result = metrics({**FINAL, 'prompt_eval_count': bad, 'prompt_eval_cached_count': bad}, 1, None, None)
                self.assertIsNone(result['prompt_tokens'])
                self.assertIsNone(result['prompt_cached_tokens'])
                self.assertIsNone(result['total_tokens'])
        result = metrics({**FINAL, 'eval_count': 0, 'prompt_eval_count': 0, 'prompt_eval_cached_count': 0}, 1, None, None)
        self.assertEqual(result['total_tokens'], 0)
        self.assertEqual(result['prompt_cached_tokens'], 0)

    def test_accumulated_usage_excludes_failed_and_cancelled(self):
        first = {'status': 'completed', **metrics(FINAL, 3, .1, .1)}
        second = {**first, 'status': 'failed', 'tokens': 999}
        third = {**second, 'status': 'cancelled'}
        result = usage([first, second, third])
        self.assertEqual(result, {'completed_runs': 1, 'excluded_runs': 2, 'prompt_tokens': 11, 'tokens': 18, 'prompt_cached_tokens': 8, 'total_tokens': 29})
        self.assertIsNone(usage([second, third])['tokens'])
        self.assertIsNone(usage([])['total_tokens'])

    def test_missing_counter_does_not_silently_become_zero(self):
        row = {'status': 'completed', 'prompt_tokens': None, 'tokens': 0, 'prompt_cached_tokens': 0, 'total_tokens': None}
        result = usage([row])
        self.assertEqual(result['tokens'], 0)
        self.assertIsNone(result['prompt_tokens'])
        self.assertIsNone(result['total_tokens'])

    def test_csv_contains_total_without_changing_old_columns(self):
        row = {'model': 'live:small', 'run': 1, 'status': 'completed', 'output_tokens_observed': 18, 'token_observation_status': 'matched', **metrics(FINAL, 3, .1, .1)}
        exported = csv_export({'settings': {**SETTINGS, 'live_token_count': True}, 'rows': [row], 'started_at': 'example'})
        result = next(csv.DictReader(io.StringIO(exported.lstrip('\ufeff'))))
        self.assertEqual(result['total_tokens'], '29')
        self.assertEqual(result['tokens'], '18')
        self.assertEqual(result['prompt_cached_tokens'], '8')
        self.assertEqual(result['live_token_count'], 'True')
        self.assertEqual(result['output_tokens_observed'], '18')
        self.assertEqual(result['token_observation_status'], 'matched')


class LiveClientTests(LiveFixture):
    def test_logprob_entries_not_chunks_count_observed_tokens(self):
        entry = {'token': 'segredo-metadado', 'logprob': -.1, 'top_logprobs': []}
        self.server.chunks = [
            {'response': 'Olá', 'logprobs': [entry, entry]},
            {'response': ' mundo', 'logprobs': [entry, entry, entry]},
        ]
        self.server.final['eval_count'] = 5
        events = []
        result = self.client.generate('live:small', {**SETTINGS, 'live_token_count': True}, threading.Event(), progress=events.append)
        self.assertEqual(result['output_tokens_observed'], 5)
        self.assertEqual(result['tokens'], 5)
        self.assertEqual(result['token_observation_status'], 'matched')
        self.assertEqual(events[-1]['fragments'], 2)
        partial = next(event for event in events if event['fragments'] and event['count_status'] == 'pending')
        self.assertEqual(partial['output_tokens_observed'], 2)
        self.assertIsNone(partial['tokens'])
        self.assertTrue(self.server.requests[-1]['logprobs'])
        self.assertEqual(self.server.requests[-1]['top_logprobs'], 0)
        self.assertNotIn('segredo-metadado', json.dumps([events, result]))
        self.assertNotIn('logprobs', result)

    def test_logprob_mismatch_keeps_final_authoritative(self):
        self.server.chunks = [{'response': 'x', 'logprobs': [{'token': 'x', 'logprob': -.1}]}]
        result = self.client.generate('live:small', {**SETTINGS, 'live_token_count': True}, threading.Event())
        self.assertEqual(result['output_tokens_observed'], 1)
        self.assertEqual(result['tokens'], 18)
        self.assertEqual(result['total_tokens'], 29)
        self.assertEqual(result['token_observation_status'], 'mismatch')

    def test_missing_or_malformed_logprobs_invalidates_attempt(self):
        valid = {'token': 'x', 'logprob': -.1}
        cases = [None, [], {}, 'bad', [{'token': 'x', 'logprob': True}], [{'token': 'x', 'logprob': float('inf')}], [{'token': 3, 'logprob': -.1}]]
        for value in cases:
            with self.subTest(value=value):
                self.server.chunks = [
                    {'response': 'a', 'logprobs': [valid]},
                    {'response': 'b', 'logprobs': value},
                    {'response': 'c', 'logprobs': [valid]},
                ]
                result = self.client.generate('live:small', {**SETTINGS, 'live_token_count': True}, threading.Event())
                self.assertIsNone(result['output_tokens_observed'])
                self.assertEqual(result['token_observation_status'], 'unavailable')
                self.assertEqual(result['tokens'], 18)
        self.server.chunks = [{'response': 'a', 'logprobs': [valid]}, {'response': 'b'}]
        result = self.client.generate('live:small', {**SETTINGS, 'live_token_count': True}, threading.Event())
        self.assertIsNone(result['output_tokens_observed'])
        self.assertEqual(result['token_observation_status'], 'unavailable')

    def test_unsupported_logprobs_fails_without_retry(self):
        self.server.mode = 'unsupported'
        events = []
        with self.assertRaisesRegex(ValueError, 'Ollama HTTP 400'):
            self.client.generate('live:small', {**SETTINGS, 'live_token_count': True}, threading.Event(), progress=events.append)
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(events[-1]['status'], 'failed')
        self.assertEqual(events[-1]['token_observation_status'], 'unavailable')
        self.assertIsNone(events[-1]['output_tokens_observed'])

    def test_cancelled_observation_is_not_presented_as_a_final_count(self):
        self.server.mode = 'blocking'
        self.server.chunks = [{'response': 'Olá', 'logprobs': [{'token': 'Olá', 'logprob': -.1}]}]
        self.manager = BenchmarkManager(self.client)
        self.manager.start({**SETTINGS, 'live_token_count': True})
        partial = self.waiting_snapshot()
        self.assertEqual(partial['live']['output_tokens_observed'], 1)
        self.assertIsNone(partial['live']['tokens'])
        self.manager.cancel()
        self.manager.thread.join(3)
        final = self.manager.snapshot()
        self.assertEqual(final['live']['token_observation_status'], 'unavailable')
        self.assertIsNone(final['live']['output_tokens_observed'])
        self.assertIsNone(final['rows'][0]['output_tokens_observed'])
        self.assertEqual(final['rows'][0]['token_observation_status'], 'unavailable')

    def test_disabled_observation_does_not_change_payload(self):
        result = self.client.generate('live:small', SETTINGS, threading.Event())
        self.assertIsNone(result['output_tokens_observed'])
        self.assertEqual(result['token_observation_status'], 'disabled')
        self.assertNotIn('logprobs', self.server.requests[-1])
        self.assertNotIn('top_logprobs', self.server.requests[-1])

    def test_progress_stays_pending_until_authoritative_final(self):
        events = []
        result = self.client.generate('live:small', SETTINGS, threading.Event(), progress=lambda event: events.append(copy.deepcopy(event)))
        partial = next(event for event in events if event['response'] and event['count_status'] == 'pending')
        self.assertIsNone(partial['tokens'])
        self.assertIsNone(partial['total_tokens'])
        self.assertEqual(partial['fragments'], 1)
        self.assertEqual(events[-1]['count_status'], 'final')
        self.assertEqual(events[-1]['total_tokens'], result['total_tokens'])

    def test_fast_chunks_throttled_but_last_preview_published(self):
        self.server.mode = 'fast'
        events = []
        ticks = count(0, .001)
        with patch('backend.ollama.time.perf_counter', side_effect=lambda: next(ticks)):
            result = self.client.generate('live:small', SETTINGS, threading.Event(), progress=events.append)
        self.assertLessEqual(len(events), 3)
        self.assertEqual(events[-1]['fragments'], 20)
        self.assertEqual(events[-1]['response'], result['response'])
        self.assertEqual(events[-1]['output_characters'], len(result['response']))

    def test_preview_bounded_and_reasoning_only_counted(self):
        self.server.mode = 'large'
        events = []
        result = self.client.generate('live:small', SETTINGS, threading.Event(), progress=events.append)
        self.assertEqual(len(result['response']), 64000)
        self.assertEqual(events[-1]['output_characters'], 100000)
        self.assertEqual(events[-1]['thinking_characters'], len('raciocínio que não deve ser armazenado'))
        self.assertFalse(any('raciocínio que não deve ser armazenado' in json.dumps(event, ensure_ascii=False) for event in events))
        self.assertTrue(all(len(event['response']) <= 64000 for event in events))

    def test_error_publishes_last_incomplete_preview_without_tokens(self):
        self.server.mode = 'error'
        events = []
        with self.assertRaisesRegex(ValueError, 'falha de geração'):
            self.client.generate('live:small', SETTINGS, threading.Event(), progress=events.append)
        self.assertEqual(events[-1]['response'], 'Olá')
        self.assertEqual(events[-1]['status'], 'failed')
        self.assertEqual(events[-1]['count_status'], 'unavailable')
        self.assertIsNone(events[-1]['tokens'])

    def test_manager_partial_snapshot_precedes_done_and_clock_advances(self):
        self.server.mode = 'blocking'
        self.manager = BenchmarkManager(self.client)
        self.manager.start(SETTINGS)
        before = self.waiting_snapshot()
        self.assertEqual(before['status'], 'running')
        self.assertEqual(before['rows'], [])
        self.assertEqual(before['live']['response'], 'Olá')
        self.assertIsNone(before['live']['tokens'])
        self.assertEqual(before['usage']['completed_runs'], 0)
        self.assertIsNone(before['usage']['tokens'])
        time.sleep(.03)
        self.assertGreater(self.manager.snapshot()['live']['elapsed_s'], before['live']['elapsed_s'])
        self.server.release.set()
        self.manager.thread.join(3)
        final = self.manager.snapshot()
        self.assertEqual(final['status'], 'completed')
        self.assertEqual(final['usage']['total_tokens'], 58)
        self.assertEqual(final['live']['total_tokens'], 29)
        self.assertEqual(final['live']['run'], 2)

    def test_cancel_retains_incomplete_preview_and_new_job_resets(self):
        self.server.mode = 'blocking'
        self.manager = BenchmarkManager(self.client)
        self.manager.start(SETTINGS)
        self.waiting_snapshot()
        self.manager.cancel()
        self.manager.thread.join(3)
        cancelled = self.manager.snapshot()
        self.assertEqual(cancelled['status'], 'cancelled')
        self.assertEqual(cancelled['live']['response'], 'Olá')
        self.assertEqual(cancelled['live']['count_status'], 'unavailable')
        self.assertIsNone(cancelled['live']['tokens'])
        self.assertEqual(cancelled['usage']['excluded_runs'], 1)
        self.assertIsNone(cancelled['usage']['tokens'])
        self.server.mode = 'normal'
        self.server.release.set()
        self.manager.start(SETTINGS)
        self.manager.thread.join(3)
        final = self.manager.snapshot()
        self.assertEqual(final['usage']['completed_runs'], 2)
        self.assertEqual(final['usage']['excluded_runs'], 0)
        self.assertEqual(final['live']['count_status'], 'final')
        self.assertEqual(len(final['rows']), 2)


if __name__ == '__main__':
    unittest.main()
