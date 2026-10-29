"""Synthetic prompt catalog and local static/privacy boundaries; no Ollama required."""
from collections import Counter
import http.client
import json
from pathlib import Path
import re
import threading
from types import SimpleNamespace
import unittest

from backend.http import AppServer
from test_faq import Page

ROOT = Path(__file__).resolve().parent.parent


class PromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = AppServer(('127.0.0.1', 0), SimpleNamespace())
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(2)

    def get(self, path, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            connection.request('GET', path, headers=headers or {})
            with connection.getresponse() as response:
                return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_catalog_has_eighteen_unique_synthetic_examples_in_six_cells(self):
        source = (ROOT / 'web/prompts.js').read_text()
        catalog, _end = json.JSONDecoder().raw_decode(source.split('const PROMPT_EXAMPLES = ', 1)[1])
        self.assertEqual(len(catalog), 18)
        self.assertEqual(len({item['id'] for item in catalog}), 18)
        self.assertEqual(Counter((item['type'], item['complexity']) for item in catalog),
                         {(kind, level): 3 for kind in ('code', 'non-code')
                          for level in ('simple', 'intermediate', 'advanced')})
        for item in catalog:
            self.assertEqual(set(item), {'id', 'type', 'complexity', 'title', 'description', 'prompt'})
            for value in item.values():
                self.assertIsInstance(value, str)
                self.assertTrue(value.strip())
            self.assertGreater(len(item['prompt']), 160)
            self.assertLess(len(item['prompt']), 16000)
        self.assertTrue(any('const valores' in item['prompt'] for item in catalog))
        self.assertTrue(any('somar_pares' in item['prompt'] for item in catalog))

    def test_dialog_is_outside_benchmark_form_and_controls_are_labelled(self):
        body = self.get('/')[2].decode()
        page = Page(body)
        self.assertFalse(page.duplicates)
        elements = {attrs.get('id'): (tag, attrs) for tag, attrs in page.elements if attrs.get('id')}
        self.assertEqual(elements['prompts-dialog'][0], 'dialog')
        self.assertIn('aria-labelledby', elements['prompts-dialog'][1])
        self.assertGreater(body.index('<dialog id="prompts-dialog"'), body.index('</form>'))
        self.assertIn('aria-haspopup', elements['prompts-open'][1])
        self.assertLess(body.index('id="settings-title"'), body.index('id="prompts-open"'))
        self.assertLess(body.index('id="prompts-open"'), body.index('<label for="prompt"'))
        self.assertIn('section-head prompts-section-head', body)
        for name in ('open', 'close', 'cancel', 'apply'):
            self.assertEqual(elements['prompts-' + name][1]['type'], 'button')
        self.assertIn('disabled', elements['prompts-apply'][1])
        self.assertEqual(elements['prompts-replace-confirm'][1]['type'], 'checkbox')
        labels = {attrs.get('for') for tag, attrs in page.elements if tag == 'label'}
        self.assertTrue({'prompts-type', 'prompts-complexity', 'prompts-replace-confirm'} <= labels)
        self.assertNotIn('Benchmark local</p>', body)
        self.assertEqual(body.count('Guia de tokens, tempos e custos'), 1)
        self.assertLess(body.index('Guia de tokens, tempos e custos'), body.index('class="header-description"'))
        self.assertIn('system-hostname', page.ids)

    def test_assets_keep_csp_host_origin_and_no_token_boundary(self):
        for path, content_type in [('/prompts.js', 'text/javascript'), ('/prompts.css', 'text/css')]:
            status, headers, body = self.get(path)
            self.assertEqual(status, 200)
            self.assertIn(content_type, headers['Content-Type'])
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
            self.assertNotIn('unsafe-inline', headers['Content-Security-Policy'])
            self.assertNotIn(self.server.token.encode(), body)
            self.assertNotIn(b'__TOKEN__', body)
            for bad in [{'Host': 'evil.example'}, {'Origin': 'https://evil.example'}, {'Sec-Fetch-Site': 'cross-site'}]:
                self.assertEqual(self.get(path, bad)[0], 403)
        self.assertEqual(self.get('/prompts/../../app.py')[0], 404)

    def test_catalog_never_uses_inference_persistence_or_offline_cache(self):
        source = self.get('/prompts.js')[2].decode()
        for forbidden in ('fetch(', '/api/', 'innerHTML', 'localStorage', 'sessionStorage', 'eval(', 'new Function', 'benchmark-token'):
            self.assertNotIn(forbidden, source)
        sw = self.get('/sw.js')[2].decode()
        block = re.search(r'const PUBLIC_ASSETS = \[(.*?)\];', sw, re.S).group(1)
        self.assertNotIn('/prompts.js', block)
        self.assertNotIn('/prompts.css', block)
        self.assertIn("CACHE_PREFIX + 'v3'", sw)
        self.assertNotIn('/prompts.js', self.get('/faq.html')[2].decode())
        self.assertIn('textContent', source)
        self.assertIn("window.addEventListener('benchmark-status'", source)
        self.assertIn('textarea.disabled', source)
        self.assertIn('consentText === textarea.value', source)
        self.assertIn('consentSelection === selected?.id', source)
        self.assertIn('dialog.showModal()', source)
        self.assertIn('opener.focus()', source)
        self.assertIn('lastApplied = textarea.defaultValue', source)
