"""Lifecycle checks use temporary checkout state and synthetic process identities."""
from contextlib import ExitStack
import copy
import io
import json
import os
from pathlib import Path
import signal
import socket
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import service


class ServiceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'checkout with spaces'
        self.root.mkdir()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in [('ROOT', self.root), ('STATE', self.root / 'service.local.json'),
                            ('LOG', self.root / 'service.local.log'), ('LOCK', self.root / 'service.local.lock')]:
            self.stack.enter_context(patch.object(service, name, value))
        self.stack.enter_context(patch('sys.stdout', new_callable=io.StringIO))
        command = service.application_args(8765)
        self.identity = {'pid': 424242, 'created': 'synthetic-boot:12345',
                         'exe': command[0], 'command': service.expected_command(command)}
        self.state = {'version': 1, 'pid': 424242, 'port': 8765,
                      'root': str(self.root), 'identity': self.identity}

    def save_fixture(self, value=None):
        service.STATE.write_text(json.dumps(self.state if value is None else value))

    def test_state_missing_corrupt_or_other_checkout_never_controls_a_process(self):
        self.assertIsNone(service.read_state())
        service.STATE.write_text('{not json')
        with self.assertRaises(ValueError):
            service.read_state()
        service.STATE.write_text('x' * 65537)
        with self.assertRaises(ValueError):
            service.read_state()
        other = {**self.state, 'root': str(self.root / 'other')}
        self.save_fixture(other)
        with self.assertRaises(ValueError):
            service.read_state()
        self.assertTrue(service.STATE.exists())
        self.save_fixture({**self.state, 'version': True})
        with self.assertRaises(ValueError):
            service.read_state()
        invalid = copy.deepcopy(self.state)
        invalid['identity']['exe'] = None
        self.save_fixture(invalid)
        with patch('sys.stderr', new_callable=io.StringIO) as errors, \
                patch.object(service, 'process_identity') as identity:
            self.assertEqual(service.main(['stop']), 1)
        identity.assert_not_called()
        self.assertNotIn('Traceback', errors.getvalue())
        self.assertTrue(service.STATE.exists())

    def test_state_requires_creation_executable_and_this_exact_command(self):
        self.save_fixture()
        self.assertEqual(service.read_state(), self.state)
        for field, replacement in [('created', ''), ('created', None), ('exe', '/different/python'),
                                   ('exe', None), ('command', None),
                                   ('command', ['python', 'other.py']), ('pid', 123), ('pid', True)]:
            with self.subTest(field=field):
                altered = copy.deepcopy(self.state)
                altered['identity'][field] = replacement
                self.save_fixture(altered)
                with self.assertRaises(ValueError):
                    service.read_state()

    def test_atomic_state_is_private_and_keeps_previous_file_on_replace_failure(self):
        service.write_state(self.state)
        self.assertEqual(service.read_state(), self.state)
        if os.name != 'nt':
            self.assertEqual(service.STATE.stat().st_mode & 0o777, 0o600)
        before = service.STATE.read_bytes()
        with patch.object(service.os, 'replace', side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):
                service.write_state({**self.state, 'port': 8766})
        self.assertEqual(service.STATE.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.service.local.*.tmp')), [])

    def test_start_is_idempotent_for_the_recorded_process(self):
        self.save_fixture()
        with patch.object(service, 'process_identity', return_value=self.identity), \
                patch.object(service.subprocess, 'Popen') as spawn, \
                patch.object(service, 'port_available') as available:
            service.start_native(8765)
        spawn.assert_not_called()
        available.assert_not_called()
        self.assertEqual(service.read_state(), self.state)

    def test_reused_pid_refuses_start_and_stop_without_signalling(self):
        self.save_fixture()
        altered = {**self.identity, 'created': 'synthetic-boot:54321'}
        with patch.object(service, 'process_identity', return_value=altered), \
                patch.object(service.subprocess, 'Popen') as spawn, \
                patch.object(service.signal, 'pidfd_send_signal', create=True) as send:
            with self.assertRaises(RuntimeError):
                service.start_native(8765)
            with self.assertRaises(RuntimeError):
                service.stop_native()
        spawn.assert_not_called()
        send.assert_not_called()
        self.assertTrue(service.STATE.exists())

    def test_port_collision_does_not_spawn_or_stop_other_servers(self):
        with socket.socket() as listener:
            if service.sys.platform.startswith('linux'):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            self.assertFalse(service.port_available(port))
            with patch.object(service.subprocess, 'Popen') as spawn:
                with self.assertRaises(RuntimeError):
                    service.start_native(port)
            if service.sys.platform.startswith('linux'):
                with socket.create_connection(('127.0.0.1', port), timeout=2) as client:
                    accepted, _address = listener.accept()
                    accepted.close()
                    self.assertEqual(client.recv(1), b'')
        spawn.assert_not_called()
        self.assertFalse(service.STATE.exists())
        if service.sys.platform.startswith('linux'):
            self.assertTrue(service.port_available(port))

    def test_stop_missing_or_dead_is_idempotent_without_any_signal(self):
        with patch.object(service.signal, 'pidfd_send_signal', create=True) as send:
            service.stop_native()
            self.save_fixture()
            with patch.object(service, 'process_identity', return_value=None):
                service.stop_native()
            service.stop_native()
        send.assert_not_called()
        self.assertFalse(service.STATE.exists())

    @unittest.skipUnless(os.name != 'nt', 'pidfd flow is Linux-specific')
    def test_stop_signals_only_the_validated_pidfd(self):
        self.save_fixture()
        with patch.object(service, 'process_identity', return_value=self.identity), \
                patch.object(service.os, 'pidfd_open', return_value=999, create=True) as opened, \
                patch.object(service.signal, 'pidfd_send_signal', create=True) as send, \
                patch.object(service.select, 'select', return_value=([999], [], [])), \
                patch.object(service.os, 'close') as close:
            service.stop_native()
        opened.assert_called_once_with(424242)
        send.assert_called_once_with(999, signal.SIGINT)
        close.assert_called_once_with(999)
        self.assertFalse(service.STATE.exists())

    @unittest.skipUnless(os.name != 'nt', 'pidfd flow is Linux-specific')
    def test_identity_change_after_opening_pidfd_preserves_state_and_sends_nothing(self):
        self.save_fixture()
        identities = [self.identity, {**self.identity, 'command': ['python', 'other.py']}]
        with patch.object(service, 'process_identity', side_effect=identities), \
                patch.object(service.os, 'pidfd_open', return_value=999, create=True), \
                patch.object(service.signal, 'pidfd_send_signal', create=True) as send, \
                patch.object(service.os, 'close') as close:
            with self.assertRaises(RuntimeError):
                service.stop_native()
        send.assert_not_called()
        close.assert_called_once_with(999)
        self.assertTrue(service.STATE.exists())

    @unittest.skipUnless(os.name != 'nt', 'flock check is POSIX-specific')
    def test_lifecycle_lock_refuses_concurrent_controller_then_releases(self):
        with service.lifecycle_lock():
            with self.assertRaises(BlockingIOError):
                with service.lifecycle_lock():
                    self.fail('Concurrent lock acquired')
        with service.lifecycle_lock():
            self.assertTrue(service.LOCK.exists())

    def test_compose_is_scoped_to_checkout_and_does_not_remove_volumes(self):
        for platform, filename in [('linux', 'compose.linux.yaml'), ('win32', 'compose.yaml')]:
            with self.subTest(platform=platform), patch.object(service.sys, 'platform', platform):
                prefix = ['docker', 'compose', '--project-directory', str(self.root),
                          '-f', str(self.root / filename)]
                self.assertEqual(service.compose_args('start', 8765), prefix + ['up', '-d', '--build', 'benchmark'])
                self.assertEqual(service.compose_args('stop', 8765), prefix + ['stop', 'benchmark'])
                with self.assertRaises(ValueError):
                    service.compose_args('start', 8766)
                for forbidden in ('down', 'prune', '--volumes', '--all'):
                    self.assertNotIn(forbidden, service.compose_args('stop', 8765))

    def test_docker_start_refuses_occupied_port_without_healthy_project_container(self):
        for identifier in [None, 'synthetic-project-container']:
            with self.subTest(identifier=identifier), \
                    patch.object(service.shutil, 'which', return_value='/synthetic/docker'), \
                    patch.object(service, 'validate_compose_ownership'), \
                    patch.object(service, 'container_id', return_value=identifier), \
                    patch.object(service, 'container_healthy', return_value=False) as health, \
                    patch.object(service, 'port_available', return_value=False), \
                    patch.object(service.subprocess, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'Porta ocupada'):
                    service.run_compose('start', 8765)
                run.assert_not_called()
                if identifier is None:
                    health.assert_not_called()
                else:
                    health.assert_called_once_with(identifier, 8765)

    def test_docker_start_is_idempotent_only_for_healthy_project_container(self):
        with patch.object(service.shutil, 'which', return_value='/synthetic/docker'), \
                    patch.object(service, 'validate_compose_ownership'), \
                patch.object(service, 'container_id', return_value='synthetic-project-container'), \
                patch.object(service, 'container_healthy', return_value=True) as health, \
                patch.object(service, 'port_available', return_value=False), \
                patch.object(service.subprocess, 'run') as run:
            service.run_compose('start', 8765)
        run.assert_not_called()
        health.assert_called_once_with('synthetic-project-container', 8765)

    def test_compose_success_without_confirmed_readiness_is_failure(self):
        with patch.object(service.shutil, 'which', return_value='/synthetic/docker'), \
                    patch.object(service, 'validate_compose_ownership'), \
                patch.object(service, 'container_id', return_value='synthetic-project-container'), \
                patch.object(service, 'container_healthy', return_value=False), \
                patch.object(service, 'port_available', return_value=True), \
                patch.object(service.time, 'monotonic', side_effect=[0, 1, 16]), \
                patch.object(service.time, 'sleep') as sleep, \
                patch.object(service.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'nao ficou pronto'):
                service.run_compose('start', 8765)
        run.assert_called_once_with(service.compose_args('start', 8765), cwd=self.root, check=True)
        sleep.assert_called_once_with(.2)

    def test_container_health_rejects_native_app_or_other_hostname(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        for value in [
            {'hostname': 'synthetic-container', 'environment': {'kind': 'native'}},
            {'hostname': 'different-container', 'environment': {'kind': 'container'}},
        ]:
            opener = MagicMock()
            opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(value).encode()
            with self.subTest(value=value), \
                    patch.object(service.subprocess, 'run', return_value=SimpleNamespace(stdout='synthetic-container\n')), \
                    patch.object(service.urllib.request, 'build_opener', return_value=opener), \
                    patch.object(service, 'healthy', return_value=True):
                self.assertFalse(service.container_healthy('synthetic-project-container', 8765))
            opener.open.assert_called_once_with('http://127.0.0.1:8765/api/system', timeout=.5)

    def test_compose_ownership_checks_stopped_containers_checkout_and_config(self):
        from types import SimpleNamespace
        prefix = service.compose_prefix()
        expected_file = prefix[-1]
        other_file = 'compose.yaml' if Path(expected_file).name == 'compose.linux.yaml' else 'compose.linux.yaml'
        for directory, config, valid in [
            (str(self.root), expected_file, True),
            (str(self.root / 'other checkout'), expected_file, False),
            (str(self.root), str(self.root / other_file), False),
        ]:
            inspected = '\n'.join(json.dumps(item) for item in (directory, config))
            with self.subTest(directory=directory, config=config), \
                    patch.object(service.subprocess, 'run', side_effect=[
                        SimpleNamespace(stdout='a' * 64 + '\n'), SimpleNamespace(stdout=inspected),
                    ]) as run:
                if valid:
                    service.validate_compose_ownership(prefix)
                else:
                    with self.assertRaisesRegex(RuntimeError, 'outro checkout/configuracao'):
                        service.validate_compose_ownership(prefix)
            self.assertEqual(run.call_args_list[0].args[0], prefix + ['ps', '--all', '--quiet'])
            self.assertIn('com.docker.compose.project.working_dir', run.call_args_list[1].args[0][3])
            self.assertIn('com.docker.compose.project.config_files', run.call_args_list[1].args[0][3])

    def test_compose_refuses_wrong_ownership_before_start_or_stop(self):
        for action in ['start', 'stop']:
            with self.subTest(action=action), \
                    patch.object(service.shutil, 'which', return_value='/synthetic/docker'), \
                    patch.object(service, 'validate_compose_ownership', side_effect=RuntimeError('synthetic ownership mismatch')) as validate, \
                    patch.object(service, 'container_id') as identifier, \
                    patch.object(service.subprocess, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'ownership mismatch'):
                    service.run_compose(action, 8765)
            validate.assert_called_once_with(service.compose_prefix())
            identifier.assert_not_called()
            run.assert_not_called()

    def test_operational_symlinks_and_reparse_attributes_never_touch_the_target(self):
        from types import SimpleNamespace
        target = self.root / 'sentinel.txt'
        target.write_bytes(b'preserve synthetic target')
        for name in ['STATE', 'LOCK', 'LOG']:
            path = getattr(service, name)
            try:
                path.symlink_to(target)
            except OSError:
                self.skipTest('Symlink creation unavailable for this account')
            try:
                with self.subTest(name=name), patch.object(service.subprocess, 'Popen') as spawn:
                    with self.assertRaises(ValueError):
                        if name == 'STATE':
                            service.read_state()
                        elif name == 'LOCK':
                            with service.lifecycle_lock():
                                self.fail('Unsafe lock acquired')
                        else:
                            with patch.object(service, 'port_available', return_value=True):
                                service.start_native(8765)
                    spawn.assert_not_called()
                self.assertEqual(target.read_bytes(), b'preserve synthetic target')
            finally:
                path.unlink()
        ordinary = target.stat()
        reparse = SimpleNamespace(st_mode=ordinary.st_mode, st_nlink=1, st_file_attributes=0x400)
        with patch.object(Path, 'lstat', return_value=reparse), patch.object(service.os, 'open') as opened:
            with self.assertRaises(ValueError):
                service.local_descriptor(service.LOG, os.O_WRONLY, create=True)
        opened.assert_not_called()
        self.assertEqual(target.read_bytes(), b'preserve synthetic target')


class PowerShellWrapperTests(unittest.TestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('pwsh'), 'pwsh/Linux wrapper fixture')
    def test_multiple_python_commands_choose_one_without_running_the_app(self):
        project = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'checkout com espacos e acento á'
            root.mkdir()
            executable = root / 'fake python'
            executable.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" >> "$FAKE_PYTHON_LOG"\nexit 0\n')
            executable.chmod(0o700)
            log = root / 'arguments.txt'
            driver = root / 'driver.ps1'
            driver.write_text("""param([string]$Wrapper,[string]$Mode)
function Get-Command {
    param([string]$Name,[string]$CommandType,[string]$ErrorAction)
    if ($Name -eq 'python3') {
        return @([pscustomobject]@{Source=$env:FAKE_PYTHON_ONE}, [pscustomobject]@{Source=$env:FAKE_PYTHON_TWO})
    }
    return $null
}
if($Mode -eq 'docker'){ & $Wrapper -Docker } else { & $Wrapper -Port 8766 }
exit $LASTEXITCODE
""", encoding='utf-8')
            environment = os.environ.copy()
            environment.update(FAKE_PYTHON_ONE=str(executable), FAKE_PYTHON_TWO=str(root / 'not executable'), FAKE_PYTHON_LOG=str(log))
            for action, mode in [('start', 'native'), ('stop', 'docker')]:
                with self.subTest(action=action):
                    result = subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-File', str(driver),
                                             str(project / (action + '.ps1')), mode], env=environment,
                                            capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
            arguments = log.read_text()
            self.assertIn(str(project / 'scripts/service.py'), arguments)
            self.assertIn('start\n--port\n8766', arguments)
            self.assertIn('stop\n--port\n8765\n--docker', arguments)
            self.assertNotIn('not executable', arguments)
