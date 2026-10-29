"""Synthetic system inventory fixtures; never inspect the developer's hardware."""
import copy
from contextlib import nullcontext
import ctypes
import http.client
import json
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import Mock, patch

from backend.http import AppServer
from backend.manager import BenchmarkManager
from backend.system_info import SystemCollector
from backend import system_info as system

STATIC = {
    'hostname': 'example-host',
    'environment': {'kind': 'native', 'scope': 'backend_process', 'note': 'Ambiente sintético'},
    'os': {'name': 'Example Linux', 'kernel': '1.2.3-example', 'architecture': 'Python 64 bits (ISA não informada)'},
    'cpu': {'model': 'Example CPU', 'physical_cores': 2, 'logical_cpus': 4, 'scope': 'process_visible_not_exclusive'},
    'gpu': {'models': ['Example Graphics'], 'scope': 'process_visible', 'note': 'Informação sintética'},
    'uptime_scope': 'kernel',
}
DYNAMIC = {
    'memory': {'total_bytes': 1024, 'used_bytes': 256, 'available_bytes': 768, 'scope': 'system_memory'},
    'disk': {'total_bytes': 8192, 'used_bytes': 2048, 'scope': 'app_filesystem'},
    'uptime_seconds': 123.5,
}


def files(values):
    return lambda path, limit=65536: values.get(str(path), '')


def collector(static=None, dynamic=None, **options):
    return SystemCollector(static_source=lambda: copy.deepcopy(STATIC if static is None else static), dynamic_source=dynamic or (lambda: copy.deepcopy(DYNAMIC)), utc_now=lambda: '2026-01-01T00:00:00+00:00', **options)


class SystemFixtureTests(unittest.TestCase):
    def test_distinct_instances_use_their_own_static_facts(self):
        alternate = copy.deepcopy(STATIC)
        alternate['os']['name'] = 'Other Example OS'
        alternate['cpu']['model'] = 'Other Example CPU'
        alternate['gpu']['models'] = ['Other Example Graphics']
        first, second = collector().snapshot(), collector(alternate).snapshot()
        self.assertNotEqual(first['os']['name'], second['os']['name'])
        self.assertNotEqual(first['cpu']['model'], second['cpu']['model'])
        self.assertNotEqual(first['gpu']['models'], second['gpu']['models'])

    def test_malformed_static_sources_fall_back_to_unknown(self):
        for bad in [None, [], {'environment': None, 'cpu': [], 'gpu': {'models': None}}, {'environment': {'kind': []}, 'gpu': {'models': 'not-a-list'}}]:
            with self.subTest(value=bad):
                value = SystemCollector(static_source=lambda: bad, dynamic_source=lambda: DYNAMIC).snapshot()
                self.assertEqual(value['environment']['kind'], 'unknown')
                self.assertEqual(value['gpu']['models'], [])
                self.assertIsNone(value['cpu']['model'])

    def test_static_source_read_once_and_dynamic_throttled(self):
        now = [0]
        static, dynamic = Mock(return_value=STATIC), Mock(return_value=DYNAMIC)
        value = SystemCollector(static_source=static, dynamic_source=dynamic, clock=lambda: now[0], utc_now=lambda: 'example')
        value.snapshot()
        now[0] = 9.9
        value.snapshot()
        self.assertEqual(dynamic.call_count, 1)
        now[0] = 10
        value.snapshot()
        self.assertEqual(dynamic.call_count, 2)
        static.assert_called_once()

    def test_busy_without_previous_snapshot_does_not_collect(self):
        dynamic = Mock(return_value=DYNAMIC)
        value = collector(dynamic=dynamic).snapshot(busy=True)
        dynamic.assert_not_called()
        self.assertIsNone(value['collected_at'])
        self.assertIsNone(value['memory']['used_bytes'])
        self.assertTrue(value['refresh']['paused'])
        self.assertTrue(value['refresh']['stale'])

    def test_busy_preserves_previous_snapshot_and_refreshes_afterward(self):
        now = [0]
        dynamic = Mock(return_value=DYNAMIC)
        value = collector(dynamic=dynamic, clock=lambda: now[0])
        original = value.snapshot()
        now[0] = 20
        paused = value.snapshot(busy=True)
        self.assertEqual(paused['memory'], original['memory'])
        self.assertEqual(dynamic.call_count, 1)
        self.assertTrue(paused['refresh']['paused'])
        value.snapshot()
        self.assertEqual(dynamic.call_count, 2)

    def test_dynamic_collection_does_not_hold_collector_lock(self):
        entered, release = threading.Event(), threading.Event()
        def dynamic():
            entered.set()
            release.wait(2)
            return DYNAMIC
        value = collector(dynamic=dynamic)
        thread = threading.Thread(target=value.snapshot)
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertTrue(value._lock.acquire(timeout=.1))
            value._lock.release()
            self.assertTrue(value.snapshot(busy=True)['refresh']['paused'])
        finally:
            release.set()
            thread.join(2)
        self.assertFalse(thread.is_alive())

    def test_failures_keep_unknown_distinct_from_zero_and_throttle_retries(self):
        dynamic = Mock(side_effect=OSError('synthetic source unavailable'))
        now = [0]
        value = collector(dynamic=dynamic, clock=lambda: now[0])
        result = value.snapshot()
        self.assertTrue(result['refresh']['stale'])
        self.assertIsNone(result['memory']['total_bytes'])
        value.snapshot()
        self.assertEqual(dynamic.call_count, 1)
        zeros = copy.deepcopy(DYNAMIC)
        zeros['memory'].update(total_bytes=0, used_bytes=0, available_bytes=0)
        zeros['uptime_seconds'] = 0
        result = collector(dynamic=lambda: zeros).snapshot()
        self.assertEqual(result['memory']['total_bytes'], 0)
        self.assertEqual(result['uptime_seconds'], 0)

    def test_requested_hostname_is_sanitized_and_failure_is_unknown(self):
        with patch.object(system.socket, 'gethostname', return_value='example-host\n\x00'):
            self.assertEqual(system._hostname(), 'example-host')
        with patch.object(system.socket, 'gethostname', side_effect=OSError('synthetic')):
            self.assertIsNone(system._hostname())
        self.assertEqual(collector().snapshot()['hostname'], 'example-host')
        for value in [None, '', 12, 'x' * 300]:
            fixture = copy.deepcopy(STATIC)
            fixture['hostname'] = value
            expected = 'x' * 256 if isinstance(value, str) and value else None
            self.assertEqual(collector(fixture).snapshot()['hostname'], expected)

    def test_extra_identifiers_are_not_serialized_or_persisted(self):
        private = 'SYNTHETIC-FORBIDDEN-IDENTIFIER'
        static = copy.deepcopy(STATIC)
        static.update(username=private, serial=private, mac=private)
        static['cpu']['serial'] = private
        static['gpu']['device_id'] = private
        dynamic = copy.deepcopy(DYNAMIC)
        dynamic.update(mounts=[private], path=private)
        dynamic['disk']['path'] = private
        value = collector(static, dynamic=lambda: dynamic).snapshot()
        self.assertNotIn(private, json.dumps(value))
        self.assertEqual(value['disk']['scope'], 'app_filesystem')
        self.assertEqual(set(value), {'collected_at', 'hostname', 'environment', 'os', 'cpu', 'gpu', 'memory', 'disk', 'uptime_seconds', 'uptime_scope', 'refresh'})


class LinuxSourceTests(unittest.TestCase):
    def test_linux_static_uses_whitelisted_model_and_optional_pci_names(self):
        fixture = {
            '/etc/os-release': 'PRETTY_NAME="Fixture OS"\nHOSTNAME="SYNTHETIC-FORBIDDEN"\n',
            '/proc/sys/kernel/osrelease': '1.0-fixture\n',
            '/proc/cpuinfo': 'model name : Fixture Processor\nSerial : SYNTHETIC-FORBIDDEN\n',
            '/sys/devices/system/cpu/cpu0/topology/physical_package_id': '0',
            '/sys/devices/system/cpu/cpu0/topology/core_id': '0',
            '/sys/devices/system/cpu/cpu1/topology/physical_package_id': '0',
            '/sys/devices/system/cpu/cpu1/topology/core_id': '0',
            '/sys/class/drm/card0/device/vendor': '0xabcd',
            '/sys/class/drm/card0/device/device': '0x1234',
            '/usr/share/hwdata/pci.ids': 'abcd  Fixture Vendor\n\t1234  Fixture GPU\n',
        }
        with patch.object(system.sys, 'platform', 'linux'), patch.object(system, '_exists', return_value=False), patch.object(system, '_read', side_effect=files(fixture)), patch.object(system, '_names', return_value=['card0', 'card0-HDMI-A-1']), patch.object(system.os, 'sched_getaffinity', return_value={0, 1}), patch.object(system.os, 'uname', return_value=SimpleNamespace(machine='fixture64')):
            result = system._static_info()
        self.assertEqual(result['os']['name'], 'Fixture OS')
        self.assertEqual(result['cpu']['model'], 'Fixture Processor')
        self.assertEqual(result['cpu']['physical_cores'], 1)
        self.assertEqual(result['cpu']['logical_cpus'], 2)
        self.assertEqual(result['gpu']['models'], ['Fixture Vendor Fixture GPU'])
        self.assertNotIn('SYNTHETIC-FORBIDDEN', json.dumps(result))

    def test_native_memory_and_uptime_units(self):
        fixture = {'/proc/meminfo': 'MemTotal: 100 kB\nMemAvailable: 25 kB\n', '/proc/uptime': '12.5 500.0'}
        with patch.object(system.sys, 'platform', 'linux'), patch.object(system, '_read', side_effect=files(fixture)), patch.object(system.shutil, 'disk_usage', return_value=SimpleNamespace(total=1000, used=200)):
            result = system._dynamic_info('native', 'not-returned')
        self.assertEqual(result['memory'], {'total_bytes': 102400, 'used_bytes': 76800, 'available_bytes': 25600, 'scope': 'system_memory'})
        self.assertEqual(result['uptime_seconds'], 12.5)
        self.assertNotIn('not-returned', json.dumps(result))

    def test_container_without_limit_or_device_does_not_invent_host_capacity(self):
        fixture = {'/proc/meminfo': 'MemTotal: 999999 kB\nMemAvailable: 888888 kB\n'}
        with patch.object(system, '_read', side_effect=files(fixture)), patch.object(system, '_exists', return_value=False):
            memory = system._linux_memory('container')
            gpu = system._linux_gpus('container')
        self.assertIsNone(memory['total_bytes'])
        self.assertEqual(memory['scope'], 'container_limit_unknown')
        self.assertEqual(gpu, [])

    def test_cgroup_v2_uses_lowest_known_ancestor_limit(self):
        fixture = {
            '/proc/self/cgroup': '0::/group/worker',
            '/sys/fs/cgroup/group/worker/memory.max': '2048',
            '/sys/fs/cgroup/group/worker/memory.current': '256',
            '/sys/fs/cgroup/group/memory.max': '1024',
            '/sys/fs/cgroup/group/memory.current': '512',
            '/sys/fs/cgroup/memory.max': 'max',
        }
        with patch.object(system, '_read', side_effect=files(fixture)):
            result = system._linux_memory('container')
        self.assertEqual(result, {'total_bytes': 1024, 'used_bytes': 512, 'available_bytes': 512, 'scope': 'cgroup_limit'})

    def test_cgroup_v1_and_unlimited_sentinel(self):
        fixture = {'/proc/self/cgroup': '4:memory:/example', '/sys/fs/cgroup/memory/example/memory.limit_in_bytes': '4096', '/sys/fs/cgroup/memory/example/memory.usage_in_bytes': '1024'}
        with patch.object(system, '_read', side_effect=files(fixture)):
            self.assertEqual(system._cgroup_memory()['total_bytes'], 4096)
        fixture['/sys/fs/cgroup/memory/example/memory.limit_in_bytes'] = str(1 << 62)
        with patch.object(system, '_read', side_effect=files(fixture)):
            self.assertIsNone(system._cgroup_memory())

    def test_inconsistent_memory_and_missing_sources_stay_unknown(self):
        with patch.object(system, '_read', side_effect=files({'/proc/meminfo': 'MemTotal: 10 kB\nMemAvailable: 20 kB'})):
            value = system._linux_memory('native')
        self.assertIsNone(value['used_bytes'])
        self.assertIsNone(value['available_bytes'])


class WindowsSourceTests(unittest.TestCase):
    def test_memory_structure_and_uptime_use_64_bit_api(self):
        def fill(pointer):
            status = pointer._obj
            self.assertEqual(ctypes.sizeof(status), 64)
            self.assertEqual(status.dwLength, 64)
            status.ullTotalPhys = 8 * 1024 ** 3
            status.ullAvailPhys = 3 * 1024 ** 3
            return 1
        memory = Mock(side_effect=fill)
        tick = Mock(return_value=(1 << 40))
        api = SimpleNamespace(GlobalMemoryStatusEx=memory, GetTickCount64=tick)
        result = system._windows_memory(api)
        self.assertEqual(result['used_bytes'], 5 * 1024 ** 3)
        self.assertEqual(system._windows_uptime(api), (1 << 40) / 1000)
        self.assertIs(tick.restype, ctypes.c_uint64)

    def test_windows_registry_and_display_sources_return_only_model_labels(self):
        registry = SimpleNamespace(HKEY_LOCAL_MACHINE=1, OpenKey=Mock(return_value=nullcontext(object())), QueryValueEx=Mock(return_value=('Fixture Processor', 1)))
        def enum(_name, index, pointer, _flags):
            if index:
                return 0
            pointer._obj.DeviceString = 'Fixture Graphics'
            pointer._obj.DeviceID = 'SYNTHETIC-FORBIDDEN-ID'
            pointer._obj.DeviceKey = 'SYNTHETIC-FORBIDDEN-KEY'
            return 1
        api = SimpleNamespace(user32=SimpleNamespace(EnumDisplayDevicesW=Mock(side_effect=enum)))
        with patch.dict(system.sys.modules, {'winreg': registry}), patch.object(system.sys, 'getwindowsversion', return_value=SimpleNamespace(major=10, minor=0, build=12345), create=True), patch.object(system.ctypes, 'windll', api, create=True):
            result = system._windows_static()
        self.assertEqual(result['os_name'], 'Windows')
        self.assertEqual(result['cpu_model'], 'Fixture Processor')
        self.assertEqual(result['gpu_models'], ['Fixture Graphics'])
        self.assertEqual(registry.QueryValueEx.call_args.args[1], 'ProcessorNameString')
        self.assertNotIn('SYNTHETIC-FORBIDDEN', json.dumps(result))

    def test_windows_architecture_from_native_machine_api(self):
        def architecture(_handle, _process, native):
            native._obj.value = 0xAA64
            return 1
        kernel = SimpleNamespace(GetCurrentProcess=Mock(return_value=1), IsWow64Process2=Mock(side_effect=architecture))
        with patch.object(system.sys, 'platform', 'win32'), patch.object(system.ctypes, 'windll', SimpleNamespace(kernel32=kernel), create=True):
            self.assertEqual(system._architecture(), 'ARM64')
        self.assertIs(kernel.GetCurrentProcess.restype, ctypes.c_void_p)

    def test_windows_static_fixture_and_safe_failures(self):
        windows = {'os_name': 'Fixture Windows', 'kernel': '10.0.fixture', 'cpu_model': 'Fixture Windows CPU', 'gpu_models': ['Fixture Display']}
        with patch.object(system.sys, 'platform', 'win32'), patch.object(system, '_container_kind', return_value='native'), patch.object(system, '_windows_static', return_value=windows), patch.object(system.os, 'cpu_count', return_value=8), patch.object(system, '_architecture', return_value='fixture64'):
            result = system._static_info()
        self.assertEqual(result['os']['name'], 'Fixture Windows')
        self.assertEqual(result['cpu']['logical_cpus'], 8)
        self.assertIsNone(result['cpu']['physical_cores'])
        self.assertEqual(result['gpu']['models'], ['Fixture Display'])
        with patch.object(system.sys, 'platform', 'win32'), patch.object(system, '_windows_memory', side_effect=OSError), patch.object(system, '_windows_uptime', side_effect=OSError), patch.object(system.shutil, 'disk_usage', side_effect=OSError):
            unknown = system._dynamic_info('native', 'not-returned')
        self.assertIsNone(unknown['memory']['total_bytes'])
        self.assertIsNone(unknown['uptime_seconds'])
        self.assertIsNone(unknown['disk']['total_bytes'])


class SystemHttpTests(unittest.TestCase):
    def setUp(self):
        self.manager = BenchmarkManager(SimpleNamespace())
        self.collector = collector()
        self.server = AppServer(('127.0.0.1', 0), self.manager, self.collector)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def get(self, path='/api/system', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        try:
            connection.request('GET', path, headers=headers or {})
            with connection.getresponse() as response:
                return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            connection.close()

    def test_system_endpoint_no_store_and_outside_benchmark_exports(self):
        code, headers, value = self.get()
        self.assertEqual(code, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(value['os']['name'], 'Example Linux')
        for path in ['/api/state', '/api/export']:
            self.assertNotIn('Example CPU', json.dumps(self.get(path)[2]))
            self.assertNotIn('collected_at', self.get(path)[2])

    def test_dynamic_source_runs_outside_manager_lock(self):
        def dynamic():
            available = self.manager.lock.acquire(blocking=False)
            self.assertTrue(available)
            if available:
                self.manager.lock.release()
            return DYNAMIC
        self.server.system_info = collector(dynamic=dynamic)
        self.assertEqual(self.get()[0], 200)

    def test_busy_route_uses_cached_data_without_io_under_manager_lock(self):
        dynamic = Mock(return_value=DYNAMIC)
        self.server.system_info = collector(dynamic=dynamic)
        self.get()
        with self.manager.lock:
            self.manager.state['status'] = 'running'
        value = self.get()[2]
        self.assertTrue(value['refresh']['paused'])
        self.assertEqual(dynamic.call_count, 1)
        self.assertTrue(self.manager.lock.acquire(timeout=.1))
        self.manager.lock.release()

    def test_unexpected_collector_exception_is_generic_and_private(self):
        self.server.system_info = SimpleNamespace(snapshot=Mock(side_effect=OSError('SYNTHETIC-PRIVATE-PATH')))
        code, headers, value = self.get()
        self.assertEqual(code, 503)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn('SYNTHETIC-PRIVATE-PATH', json.dumps(value))
        self.assertEqual(set(value), {'error'})

    def test_host_origin_and_absent_collector(self):
        self.assertEqual(self.get(headers={'Host': 'invalid.example'})[0], 403)
        self.assertEqual(self.get(headers={'Origin': 'https://invalid.example'})[0], 403)
        self.assertEqual(self.get(headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.server.system_info = None
        code, _headers, value = self.get()
        self.assertEqual(code, 503)
        self.assertIn('error', value)


if __name__ == '__main__':
    unittest.main()
