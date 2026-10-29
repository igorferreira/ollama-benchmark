"""Public UI/asset checks using placeholders, without collecting real hardware."""
import http.client
import json
import re
import threading
from types import SimpleNamespace
import unittest

from backend.http import AppServer
from backend.manager import BenchmarkManager
from test_faq import Page


class SystemUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A server without an injected collector must never inspect the test machine.
        cls.server = AppServer(('127.0.0.1', 0), BenchmarkManager(SimpleNamespace()))
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

    def test_environment_strip_placeholders_and_accessible_details(self):
        body = self.get('/')[2].decode()
        page = Page(body)
        self.assertFalse(page.duplicates)
        expected = {
            'system-environment', 'system-summary', 'system-details', 'system-heading',
            'system-source', 'system-os', 'system-cpu', 'system-gpu', 'system-ram',
            'system-memory-bar', 'system-toggle', 'system-close', 'system-refresh',
            'system-collected', 'system-status', 'system-note', 'system-gpu-note',
        }
        self.assertTrue(expected <= page.ids)
        elements = {attrs['id']: (tag, attrs) for tag, attrs in page.elements if 'id' in attrs}
        _tag, toggle = elements['system-toggle']
        self.assertEqual(toggle['type'], 'button')
        self.assertEqual(toggle['aria-controls'], 'system-details')
        self.assertEqual(toggle['aria-expanded'], 'false')
        self.assertIn('hidden', elements['system-details'][1])
        self.assertEqual(elements['system-details'][1]['role'], 'region')
        self.assertIn('hidden', elements['system-memory-bar'][1])
        self.assertEqual(elements['system-memory-bar'][1]['max'], '100')
        self.assertEqual(elements['system-status'][1]['role'], 'status')
        self.assertIn('Não informado', body)
        self.assertIn('não identifica a GPU usada pelo Ollama', body)
        self.assertNotIn('aria-modal', body)

    def test_system_script_is_separate_public_and_not_on_faq(self):
        page = Page(self.get('/')[2].decode())
        scripts = [attrs for tag, attrs in page.elements if tag == 'script']
        system = next(attrs for attrs in scripts if attrs.get('src') == '/system.js')
        self.assertIn('defer', system)
        self.assertTrue(all(attrs.get('src') for attrs in scripts))
        status, headers, body = self.get('/system.js')
        self.assertEqual(status, 200)
        self.assertIn('javascript', headers['Content-Type'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
        self.assertNotIn(self.server.token.encode(), body)
        self.assertNotIn(b'__TOKEN__', body)
        faq = Page(self.get('/faq.html')[2].decode())
        self.assertFalse(any(attrs.get('src') == '/system.js' for _tag, attrs in faq.elements))

    def test_inventory_is_never_added_to_public_cache_or_benchmark_export(self):
        source = self.get('/sw.js')[2].decode()
        block = re.search(r'const PUBLIC_ASSETS = \[(.*?)\];', source, re.S).group(1)
        assets = re.findall(r"'([^']+)'", block)
        self.assertIn("CACHE_PREFIX + 'v3'", source)
        self.assertNotIn('/system.js', assets)
        self.assertNotIn('/api/system', assets)
        self.assertFalse(any(path.startswith('/api/') for path in assets))
        self.assertNotIn('/', assets)
        state = json.loads(self.get('/api/state')[2])
        exported = json.loads(self.get('/api/export?format=json')[2])
        for value in [state, exported]:
            self.assertNotIn('system', value)
            self.assertNotIn('environment', value)
            self.assertNotIn('cpu', value)
        status, _headers, body = self.get('/api/system')
        self.assertEqual(status, 503)
        self.assertIn('indisponível', json.loads(body)['error'])

    def test_public_script_preserves_origin_and_payload_boundaries(self):
        for bad in [{'Host': 'evil.example'}, {'Origin': 'https://evil.example'}, {'Sec-Fetch-Site': 'cross-site'}]:
            self.assertEqual(self.get('/system.js', bad)[0], 403)
        self.assertEqual(self.get('/web/system.js')[0], 404)
        source = self.get('/system.js')[2].decode()
        self.assertNotIn('innerHTML', source)
        self.assertNotIn('localStorage', source)
        self.assertNotIn('sessionStorage', source)
        self.assertNotIn('navigator.', source)
        self.assertIn('textContent', source)
        self.assertIn("cache:'no-store'", source)
        self.assertIn('benchmark-status', source)
        self.assertIn("!document.querySelector('dialog[open]')", source)
        for event in ['pointerenter', 'focusin', 'click', 'Escape']:
            self.assertIn(event, source)


if __name__ == '__main__':
    unittest.main()
