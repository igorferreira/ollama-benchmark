"""History UI boundaries and summary-first markup without browser dependencies."""
import http.client
from pathlib import Path
import re
import threading
from types import SimpleNamespace
import unittest

from backend.http import AppServer
from test_faq import Page

ROOT = Path(__file__).resolve().parent.parent


class HistoryUiTests(unittest.TestCase):
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

    def test_history_requires_explicit_confirmation_and_is_outside_form(self):
        body = self.get('/')[2].decode()
        page = Page(body)
        self.assertFalse(page.duplicates)
        elements = {attrs.get('id'): (tag, attrs) for tag, attrs in page.elements if attrs.get('id')}
        for identifier in ['history-confirmation', 'history-confirm', 'history-apply', 'history-cancel', 'history-warning', 'history-model-warning', 'results-source']:
            self.assertIn(identifier, elements)
        self.assertNotIn('history-panel', elements)
        self.assertNotIn('history-select', elements)
        self.assertGreater(body.index('id="history-confirmation"'), body.index('</form>'))
        self.assertIn('hidden', elements['history-confirmation'][1])
        self.assertIn('disabled', elements['history-apply'][1])
        self.assertEqual(elements['history-confirm'][1]['type'], 'checkbox')
        for identifier in ['history-apply', 'history-cancel', 'history-refresh']:
            self.assertEqual(elements[identifier][1]['type'], 'button')
        labels = {attrs.get('for') for tag, attrs in page.elements if tag == 'label'}
        self.assertIn('history-confirm', labels)
        self.assertIn('Confirmo substituir a comparação atual', body)

    def test_history_assets_keep_token_and_local_http_boundary(self):
        for path, content_type in [('/history.js', 'text/javascript'), ('/history.css', 'text/css')]:
            status, headers, body = self.get(path)
            self.assertEqual(status, 200)
            self.assertIn(content_type, headers['Content-Type'])
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertNotIn('unsafe-inline', headers['Content-Security-Policy'])
            self.assertNotIn(self.server.token.encode(), body)
            for bad in [{'Host': 'evil.example'}, {'Origin': 'https://evil.example'}, {'Sec-Fetch-Site': 'cross-site'}]:
                self.assertEqual(self.get(path, bad)[0], 403)
        self.assertEqual(self.get('/history/../../app.py')[0], 404)
        script = self.get('/history.js')[2].decode()
        for forbidden in ('innerHTML', 'localStorage', 'sessionStorage', '/api/start', '/api/generate'):
            self.assertNotIn(forbidden, script)
        self.assertIn('JSON.stringify({id})', script)
        self.assertIn('items.filter(job=>job.id!==displayedId)', script)
        self.assertIn('Data de salvamento; início indisponível', script)
        self.assertIn("addEventListener('comparison-state'", script)
        self.assertIn("if(job.isCurrent){showCurrentDetails();return;}", script)
        self.assertRegex(script, r"cache\s*:\s*['\"]no-store['\"]")
        self.assertIn('response.status === 409', script)
        cache = self.get('/sw.js')[2].decode()
        assets = re.search(r'const PUBLIC_ASSETS = \[(.*?)\];', cache, re.S).group(1)
        self.assertNotIn('/history.js', assets)
        self.assertNotIn('/history.css', assets)
        self.assertNotIn('/api/history', assets)

    def test_summary_first_units_legend_and_readable_detail_structure(self):
        body = self.get('/')[2].decode()
        page = Page(body)
        self.assertLess(body.index('<tbody id="summary"'), body.index('id="live-details"'))
        self.assertIn('Data/hora da execução', body)
        self.assertIn('Datas e horas no horário do navegador', body)
        self.assertIn('Role a tabela para ver todas as métricas e ações. O modelo permanece visível.', body)
        self.assertGreater(body.index('id="install-help"'), body.index('<footer>'))
        self.assertGreater(body.index('id="install-app"'), body.index('<footer>'))
        self.assertGreater(body.index('id="install-status"'), body.index('<footer>'))
        self.assertIn('s = segundos · tokens/s = tokens de saída por segundo', body)
        self.assertIn('Como ler as métricas', body)
        self.assertGreaterEqual(body.count('aria-describedby="metric-units"'), 2)
        self.assertIn('models-selected', page.ids)
        self.assertIn('prompts-back-list', page.ids)
        attrs = next(attrs for _tag, attrs in page.elements if attrs.get('id') == 'individual-results')
        self.assertNotIn('open', attrs)
        offline = self.get('/offline.html')[2].decode()
        self.assertIn('class="offline-primary"', offline)
        self.assertIn('<pre>python3 app.py</pre>', offline)
        self.assertIn('<pre>py -3 app.py</pre>', offline)

    def test_startup_and_polling_guards_and_light_input_contrast(self):
        script = self.get('/app.js')[2].decode()
        self.assertIn('if(!formTouched&&state.settings', script)
        self.assertIn('historicalModels||', script)
        self.assertIn('revision===stateRevision', script)
        self.assertIn('document.hidden||polling', script)
        self.assertIn("addEventListener('visibilitychange'", script)
        self.assertIn('active?700:3000', script)
        self.assertIn('Math.min(30000', script)
        self.assertIn('if(active||historyLoading)return', script)
        css = self.get('/style.css')[2].decode()
        color = re.search(r'--input-border:#([0-9a-f]{6})', css).group(1)
        channels = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
        luminance = sum(v * weight for v, weight in zip(linear, [.2126, .7152, .0722]))
        self.assertGreaterEqual(1.05 / (luminance + .05), 3)
        self.assertIn('max-height:280px', css)
        self.assertIn('width:44px;height:44px', css)
        self.assertIn('position:sticky', css)
