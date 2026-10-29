"""Local lifecycle for this checkout. Uses only Python and OS-provided tools."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
import json
import os
from pathlib import Path
import select
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / 'service.local.json'
LOG = ROOT / 'service.local.log'
LOCK = ROOT / 'service.local.lock'


def application_args(port):
    return [str(Path(sys.executable).resolve()), str(ROOT / 'app.py'), '--no-browser', '--port', str(port)]



def local_descriptor(path, flags, create=False):
    try:
        before = path.lstat()
    except FileNotFoundError:
        before = None
    def regular(details):
        return (stat.S_ISREG(details.st_mode) and details.st_nlink == 1
                and not getattr(details, 'st_file_attributes', 0) & 0x400)
    if before is not None and not regular(before):
        raise ValueError('Arquivo operacional invalido; links e arquivos especiais sao recusados.')
    if before is None and create:
        flags |= os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NOINHERIT', 0), 0o600)
    try:
        actual = os.fstat(descriptor)
        current = path.lstat()
        if (not regular(actual) or not regular(current)
                or (actual.st_dev, actual.st_ino) != (current.st_dev, current.st_ino)
                or (before is not None and (actual.st_dev, actual.st_ino) != (before.st_dev, before.st_ino))):
            raise ValueError('Identidade do arquivo operacional mudou; operacao recusada.')
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


@contextmanager
def lifecycle_lock():
    descriptor = local_descriptor(LOCK, os.O_RDWR, create=True)
    with os.fdopen(descriptor, 'r+b') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.write(b'0')
            stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def windows_identity(pid):
    shell = shutil.which('powershell.exe') or shutil.which('pwsh.exe')
    if shell is None:
        raise RuntimeError('PowerShell nao encontrado para validar o processo.')
    command = ("[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); "
               "$ErrorActionPreference='Stop'; "
               f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}'; "
               "if($null -eq $p){'null'}else{"
               "@{pid=[int]$p.ProcessId;created=$p.CreationDate.ToUniversalTime().ToString('o');"
               "exe=$p.ExecutablePath;command=$p.CommandLine}|ConvertTo-Json -Compress}")
    result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-Command', command],
                            capture_output=True, timeout=10, check=True)
    value = json.loads(result.stdout.decode('utf-8-sig'))
    if value is None:
        return None
    if (not isinstance(value, dict) or type(value.get('pid')) is not int or value['pid'] != pid
            or not all(isinstance(value.get(key), str) and value[key] for key in ['exe', 'command', 'created'])):
        raise RuntimeError('Identidade do processo indisponivel; nenhuma parada foi feita.')
    value['exe'] = os.path.normcase(str(Path(value['exe']).resolve()))
    return value


def process_identity(pid):
    if os.name == 'nt':
        return windows_identity(pid)
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Controle nativo disponivel somente em Linux e Windows.')
    process = Path('/proc') / str(pid)
    try:
        fields = (process / 'stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z':
            return None
        boot = next(line.split()[1] for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime '))
        return {'pid': pid, 'created': boot + ':' + fields[19],
                'exe': str((process / 'exe').resolve(strict=True)),
                'command': [os.fsdecode(value) for value in (process / 'cmdline').read_bytes().split(b'\0') if value]}
    except (FileNotFoundError, ProcessLookupError):
        return None


def expected_command(args):
    return subprocess.list2cmdline(args) if os.name == 'nt' else args


def read_state():
    if not STATE.exists() and not STATE.is_symlink():
        return None
    if STATE.is_symlink():
        raise ValueError('Estado operacional invalido; nenhum processo foi alterado.')
    with os.fdopen(local_descriptor(STATE, os.O_RDONLY), 'rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('Estado operacional invalido; nenhum processo foi alterado.')
    value = json.loads(raw)
    if (not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1 or type(value.get('pid')) is not int
            or value['pid'] <= 0 or type(value.get('port')) is not int or not 1 <= value['port'] <= 65535
            or value.get('root') != str(ROOT) or not isinstance(value.get('identity'), dict)):
        raise ValueError('Estado operacional invalido; nenhum processo foi alterado.')
    identity = value['identity']
    args = application_args(value['port'])
    if (type(identity.get('pid')) is not int or identity['pid'] != value['pid']
            or not isinstance(identity.get('exe'), str) or not identity['exe']
            or not isinstance(identity.get('created'), str)
            or not identity['created'] or identity.get('command') != expected_command(args)
            or os.path.normcase(identity.get('exe', '')) != os.path.normcase(args[0])):
        raise ValueError('Estado operacional nao pertence a este checkout/interprete; nenhuma parada foi feita.')
    return value


def write_state(value):
    descriptor, name = tempfile.mkstemp(prefix='.service.local.', suffix='.tmp', dir=ROOT)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, STATE)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def matching_process(state):
    actual = process_identity(state['pid'])
    if actual is None:
        return False
    if actual != state['identity']:
        raise RuntimeError('PID ou identidade mudou. Nenhum processo foi encerrado ou substituido.')
    return True


def port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        if sys.platform.startswith('linux'):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(('127.0.0.1', port))
        except OSError as error:
            if error.errno in {errno.EADDRINUSE, errno.EACCES}:
                return False
            raise
    return True


def healthy(port):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f'http://127.0.0.1:{port}/api/health', timeout=.5) as response:
            return response.status == 200 and json.loads(response.read(1024)) == {'status': 'ok'}
    except (OSError, ValueError):
        return False


def start_native(port):
    state = read_state()
    if state is not None:
        if matching_process(state):
            print(f"App ja iniciado em http://127.0.0.1:{state['port']}")
            return
        STATE.unlink()
    if not port_available(port):
        raise RuntimeError('Porta ocupada ou indisponivel. Nenhum processo foi alterado.')
    args = application_args(port)
    environment = os.environ.copy()
    environment.update(APP_BIND='127.0.0.1', PYTHONUNBUFFERED='1')
    descriptor = local_descriptor(LOG, os.O_WRONLY | os.O_APPEND, create=True)
    with os.fdopen(descriptor, 'ab') as output:
        if os.name != 'nt':
            os.fchmod(output.fileno(), 0o600)
        offset = os.lseek(output.fileno(), 0, os.SEEK_END)
        options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS} if os.name == 'nt' else {'start_new_session': True}
        child = subprocess.Popen(args, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                 stdout=output, stderr=subprocess.STDOUT, **options)
    try:
        ready = f'Ollama Benchmark: http://127.0.0.1:{port}'.encode()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError('App nao iniciou. Consulte o log operacional local.')
            with LOG.open('rb') as stream:
                stream.seek(offset)
                announced = ready in stream.read(65536).splitlines()
            if announced and healthy(port):
                identity = process_identity(child.pid)
                if identity is None or identity['command'] != expected_command(args):
                    raise RuntimeError('Nao foi possivel validar o processo iniciado.')
                write_state({'version': 1, 'pid': child.pid, 'port': port,
                             'root': str(ROOT), 'identity': identity})
                print(f'App iniciado em http://127.0.0.1:{port}')
                return
            time.sleep(.1)
        raise RuntimeError('App nao ficou pronto no prazo. Consulte o log operacional local.')
    except BaseException:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
        raise


def stop_windows(state):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000 | 0x0001 | 0x00100000, False, state['pid'])
    if not handle:
        if process_identity(state['pid']) is None:
            return
        raise RuntimeError('Nao foi possivel abrir o processo para validacao segura.')
    try:
        if not matching_process(state):
            return
        if not kernel.TerminateProcess(handle, 0) or kernel.WaitForSingleObject(handle, 8000) != 0:
            raise RuntimeError('A parada nao foi confirmada; estado operacional preservado.')
    finally:
        kernel.CloseHandle(handle)


def stop_native():
    state = read_state()
    if state is None:
        print('App ja esta parado ou nao foi iniciado por estes scripts.')
        return
    if not matching_process(state):
        STATE.unlink()
        print('App ja esta parado; estado antigo removido.')
        return
    if os.name == 'nt':
        stop_windows(state)
    else:
        if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
            raise RuntimeError('Kernel/Python sem pidfd; parada automatica recusada por seguranca.')
        try:
            descriptor = os.pidfd_open(state['pid'])
        except ProcessLookupError:
            descriptor = None
        if descriptor is not None:
            try:
                if matching_process(state):
                    signal.pidfd_send_signal(descriptor, signal.SIGINT)
                    if not select.select([descriptor], [], [], 8)[0]:
                        signal.pidfd_send_signal(descriptor, signal.SIGTERM)
                        if not select.select([descriptor], [], [], 2)[0]:
                            raise RuntimeError('A parada nao foi confirmada; estado operacional preservado.')
            finally:
                os.close(descriptor)
    STATE.unlink(missing_ok=True)
    print('App parado. Historico local preservado.')


def compose_prefix():
    filename = 'compose.linux.yaml' if sys.platform.startswith('linux') else 'compose.yaml'
    return ['docker', 'compose', '--project-directory', str(ROOT), '-f', str(ROOT / filename)]


def compose_args(action, port):
    if port != 8765:
        raise ValueError('Porta customizada disponivel somente no modo nativo.')
    return compose_prefix() + (['up', '-d', '--build', 'benchmark'] if action == 'start' else ['stop', 'benchmark'])


def validate_compose_ownership(prefix):
    result = subprocess.run(prefix + ['ps', '--all', '--quiet'], cwd=ROOT,
                            capture_output=True, check=True, timeout=15, text=True)
    expected_file = prefix[-1]
    template = '{{json (index .Config.Labels "com.docker.compose.project.working_dir")}}\n{{json (index .Config.Labels "com.docker.compose.project.config_files")}}'
    for identifier in result.stdout.split():
        if not identifier.isalnum():
            raise RuntimeError('Identificador Docker invalido; operacao recusada.')
        inspected = subprocess.run(['docker', 'inspect', '--format', template, identifier],
                                   capture_output=True, check=True, timeout=10, text=True)
        lines = inspected.stdout.splitlines()
        if len(lines) != 2:
            raise RuntimeError('Propriedade do container indisponivel; operacao recusada.')
        directory, config = (json.loads(value) for value in lines)
        if (not isinstance(directory, str) or not isinstance(config, str)
                or os.path.normcase(str(Path(directory).resolve())) != os.path.normcase(str(ROOT))
                or os.path.normcase(str(Path(config).resolve())) != os.path.normcase(expected_file)):
            raise RuntimeError('Nome Compose pertence a outro checkout/configuracao; nenhum container foi alterado.')


def container_id(prefix):
    result = subprocess.run(prefix + ['ps', '--status', 'running', '--quiet', 'benchmark'],
                            cwd=ROOT, capture_output=True, check=True, timeout=15, text=True)
    identifiers = result.stdout.split()
    if len(identifiers) > 1:
        raise RuntimeError('Mais de um container encontrado; controle automatico recusado.')
    return identifiers[0] if identifiers else None


def container_healthy(identifier, port):
    result = subprocess.run(['docker', 'inspect', '--format', '{{.Config.Hostname}}', identifier],
                            capture_output=True, check=True, timeout=10, text=True)
    hostname = result.stdout.strip()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f'http://127.0.0.1:{port}/api/system', timeout=.5) as response:
            data = json.loads(response.read(65536))
        return (healthy(port) and bool(hostname) and data.get('hostname') == hostname
                and data.get('environment', {}).get('kind') == 'container')
    except (OSError, ValueError):
        return False


def run_compose(action, port):
    args = compose_args(action, port)
    if shutil.which('docker') is None:
        raise RuntimeError('Docker nao encontrado. O modo nativo usa somente Python.')
    prefix = compose_prefix()
    validate_compose_ownership(prefix)
    if action == 'stop':
        subprocess.run(args, cwd=ROOT, check=True)
        print('Container do projeto parado. Volumes preservados.')
        return
    identifier = container_id(prefix)
    if not port_available(port):
        if identifier and container_healthy(identifier, port):
            print(f'Container do projeto ja ativo em http://127.0.0.1:{port}')
            return
        raise RuntimeError('Porta ocupada por outra instancia. Pare o modo atual antes de iniciar Docker.')
    subprocess.run(args, cwd=ROOT, check=True)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        identifier = container_id(prefix)
        if identifier and container_healthy(identifier, port):
            print(f'App Docker iniciado em http://127.0.0.1:{port}')
            return
        time.sleep(.2)
    raise RuntimeError('Container nao ficou pronto no prazo; nenhum outro processo foi alterado.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop'])
    parser.add_argument('--docker', action='store_true')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        parser.error('Python 3.11 ou superior e necessario.')
    if not 1 <= args.port <= 65535:
        parser.error('Porta deve ficar entre 1 e 65535.')
    try:
        with lifecycle_lock():
            if args.docker:
                run_compose(args.action, args.port)
            elif args.action == 'start':
                start_native(args.port)
            else:
                stop_native()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('Falha no controle local: ' + (str(error) if isinstance(error, (ValueError, RuntimeError)) else 'operacao indisponivel; nenhum processo alheio foi encerrado.'), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
