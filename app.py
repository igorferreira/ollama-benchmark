"""Local browser interface for Ollama benchmarks. No third-party packages."""
from __future__ import annotations

import argparse
import os
import threading
import webbrowser

from backend.history import HistoryRepository
from backend.http import AppServer
from backend.manager import BenchmarkManager
from backend.ollama import OllamaClient
from backend.system_info import SystemCollector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port', type=int, default=int(os.environ.get('APP_PORT', '8765')))
    args = parser.parse_args()
    host = os.environ.get('APP_BIND', '127.0.0.1')
    if host not in {'127.0.0.1', '0.0.0.0'}:
        parser.error('APP_BIND deve ser 127.0.0.1 ou 0.0.0.0 (somente dentro do container).')
    client = OllamaClient(os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434'))
    manager = BenchmarkManager(client, HistoryRepository())
    server = AppServer((host, args.port), manager, SystemCollector())
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Ollama Benchmark: {url}', flush=True)
    if not args.no_browser:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nEncerrando.', flush=True)
    finally:
        server.manager.cancel()
        server.server_close()


if __name__ == '__main__':
    main()
