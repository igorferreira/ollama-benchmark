"""HTTP and public-content checks for the FAQ, help and offline privacy boundary."""
import http.client
from html.parser import HTMLParser
import re
import threading
from types import SimpleNamespace
import unittest

from backend.http import AppServer


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = set()
        self.duplicates = []
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        identifier = attrs.get('id')
        if identifier:
            if identifier in self.ids:
                self.duplicates.append(identifier)
            self.ids.add(identifier)


class FaqTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Public documentation must not need a client or running Ollama.
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

    def test_faq_public_without_ollama_token_or_api_script(self):
        status, headers, body = self.get('/faq.html')
        self.assertEqual(status, 200)
        self.assertIn('text/html', headers['Content-Type'])
        self.assertNotIn(self.server.token.encode(), body)
        self.assertNotIn(b'__TOKEN__', body)
        self.assertNotIn(b'benchmark-token', body)
        page = Page(body.decode())
        scripts = [a.get('src') for tag, a in page.elements if tag == 'script']
        self.assertEqual(scripts, ['/help.js'])
        helper = self.get('/help.js')[2]
        self.assertNotIn(b'fetch(', helper)
        self.assertNotIn(b'/api/', helper)
        self.assertNotIn(b'benchmark-token', helper)
        self.assertIn('contagem-ao-vivo', page.ids)
        self.assertEqual(len([1 for tag, _a in page.elements if tag == 'details']), 16)

    def test_faq_anchors_assets_and_shared_theme(self):
        page = Page(self.get('/faq.html')[2].decode())
        self.assertFalse(page.duplicates)
        self.assertIn('theme-select', page.ids)
        for tag, attrs in page.elements:
            href = attrs.get('href', '')
            if href.startswith('#'):
                self.assertIn(href[1:], page.ids)
            for field in ('src', 'href'):
                target = attrs.get(field, '')
                if target.startswith('/'):
                    self.assertEqual(self.get(target)[0], 200, target)
            if tag == 'script':
                self.assertTrue(attrs.get('src'), 'No inline script is permitted')

    def test_faq_and_help_keep_local_http_boundary(self):
        for path in ['/faq.html', '/help.js']:
            status, headers, body = self.get(path)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
            self.assertNotIn('unsafe-inline', headers['Content-Security-Policy'])
            self.assertNotIn(self.server.token.encode(), body)
            for bad in [{'Host': 'evil.example'}, {'Origin': 'https://evil.example'}, {'Sec-Fetch-Site': 'cross-site'}]:
                self.assertEqual(self.get(path, bad)[0], 403)
        for path in ['/faq/../../app.py', '/help/missing.js']:
            self.assertEqual(self.get(path)[0], 404)

    def test_cache_contains_only_explicit_public_resources(self):
        source = self.get('/sw.js')[2].decode()
        block = re.search(r'const PUBLIC_ASSETS = \[(.*?)\];', source, re.S).group(1)
        paths = re.findall(r"'([^']+)'", block)
        allowed = {
            '/offline.html', '/faq.html', '/help.js', '/style.css', '/manifest.webmanifest',
            '/icons/icon.svg', '/icons/icon-192.png', '/icons/icon-512.png',
            '/icons/maskable-512.png', '/icons/apple-touch-icon.png',
        }
        self.assertEqual(set(paths), allowed)
        self.assertIn("CACHE_PREFIX + 'v4'", source)
        for path in paths:
            status, _headers, body = self.get(path)
            self.assertEqual(status, 200, path)
            self.assertNotIn(self.server.token.encode(), body)
            self.assertNotIn(b'__TOKEN__', body)
        self.assertNotIn('/', paths)
        self.assertNotIn('/app.js', paths)
        self.assertNotIn('/pwa.js', paths)
        self.assertFalse(any(path.startswith('/api/') for path in paths))

    def test_help_labels_and_preview_do_not_remove_form_accessibility(self):
        text = self.get('/')[2].decode()
        page = Page(text)
        self.assertFalse(page.duplicates)
        self.assertTrue(any(tag == 'a' and attrs.get('href') == '/faq.html' for tag, attrs in page.elements))
        for tag, attrs in page.elements:
            if tag == 'button' and 'help-trigger' in attrs.get('class', ''):
                self.assertEqual(attrs.get('type'), 'button')
                self.assertTrue(attrs.get('aria-label'))
                self.assertIn(attrs.get('aria-describedby'), page.ids)
                self.assertEqual(attrs.get('aria-expanded'), 'false')
            if attrs.get('id') == 'live-response':
                self.assertNotIn('aria-live', attrs)
        labeled = {attrs.get('for') for tag, attrs in page.elements if tag == 'label'}
        self.assertTrue({'num_predict', 'num_ctx', 'repetitions', 'timeout', 'live_token_count'} <= labeled)
        checkbox = next(attrs for _tag, attrs in page.elements if attrs.get('id') == 'live_token_count')
        self.assertNotIn('checked', checkbox)
        self.assertIn('live-observed', page.ids)
        self.assertIn('usage-total', page.ids)
        helper = self.get('/help.js')[2]
        self.assertIn(b"!document.querySelector('dialog[open]')", helper)
        for event in [b'pointerenter', b'focus', b'click', b'Escape']:
            self.assertIn(event, helper)


if __name__ == '__main__':
    unittest.main()
