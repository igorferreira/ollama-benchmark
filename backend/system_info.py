"""Small, volatile backend-environment summary with a locally requested hostname."""
from __future__ import annotations

import copy
import ctypes
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import sys
import threading
import time


def _read(path, limit=65536):
    try:
        with open(path, 'rb') as source:
            data = source.read(limit + 1)
        return data.decode('utf-8', 'replace') if len(data) <= limit else ''
    except (OSError, ValueError):
        return ''


def _names(path):
    try:
        return [entry.name for entry in Path(path).iterdir()][:4096]
    except OSError:
        return []


def _exists(path):
    try:
        return Path(path).exists()
    except OSError:
        return False


def _text(value):
    if not isinstance(value, str):
        return None
    value = ''.join(character for character in value if character.isprintable()).strip()
    return value[:256] or None


def _number(value):
    if type(value) is int:
        return value if value >= 0 else None
    if type(value) is float and math.isfinite(value) and value >= 0:
        return value
    return None


def _integer(value):
    return value if type(value) is int and value >= 0 else None


def _container_kind():
    if _exists('/.dockerenv') or _exists('/run/.containerenv'):
        return 'container'
    groups = _read('/proc/self/cgroup')
    if any(marker in groups for marker in ['/docker/', '/docker-', '/kubepods', '/libpod-', '/lxc/']):
        return 'container'
    return 'native' if sys.platform in {'linux', 'win32'} else 'unknown'


def _linux_os():
    fields = {}
    for line in _read('/etc/os-release').splitlines():
        key, separator, value = line.partition('=')
        if separator and key in {'PRETTY_NAME', 'NAME', 'VERSION'}:
            fields[key] = value.strip().strip('"\'')
    return _text(fields.get('PRETTY_NAME')) or _text(' '.join(filter(None, [fields.get('NAME'), fields.get('VERSION')])))


def _linux_cpu():
    model = None
    for line in _read('/proc/cpuinfo').splitlines():
        key, separator, value = line.partition(':')
        if separator and key.strip() in {'model name', 'Processor'}:
            model = _text(value)
            if model:
                break
    try:
        visible = set(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        count = os.cpu_count()
        visible = set(range(count)) if type(count) is int and 0 < count <= 4096 else set()
    topology = set()
    for index in sorted(visible):
        package = _read(f'/sys/devices/system/cpu/cpu{index}/topology/physical_package_id', 64).strip()
        core = _read(f'/sys/devices/system/cpu/cpu{index}/topology/core_id', 64).strip()
        if not package.isdigit() or not core.isdigit():
            return model, None, len(visible) or None
        topology.add((package, core))
    return model, len(topology) or None, len(visible) or None


def _pci_model(vendor, device):
    if not re.fullmatch(r'[0-9a-f]{4}', vendor) or not re.fullmatch(r'[0-9a-f]{4}', device):
        return None
    for path in ['/usr/share/hwdata/pci.ids', '/usr/share/misc/pci.ids', '/usr/share/pci.ids']:
        vendor_name = None
        for line in _read(path, 4 * 1024 * 1024).splitlines():
            if re.match(r'^[0-9a-fA-F]{4}\s', line):
                if vendor_name:
                    break
                if line[:4].lower() == vendor:
                    vendor_name = line[4:].strip()
            elif vendor_name and re.match(r'^\t[0-9a-fA-F]{4}\s', line) and line[1:5].lower() == device:
                return _text(vendor_name + ' ' + line[5:].strip())
    return None


def _linux_gpus(kind):
    if kind == 'container' and not _exists('/dev/dri'):
        return []
    models = []
    for name in _names('/sys/class/drm'):
        if not re.fullmatch(r'card\d+', name):
            continue
        base = f'/sys/class/drm/{name}/device'
        model = _text(_read(base + '/product_name', 1024))
        if not model:
            vendor = _read(base + '/vendor', 64).strip().lower().removeprefix('0x')
            device = _read(base + '/device', 64).strip().lower().removeprefix('0x')
            model = _pci_model(vendor, device)
        if model and model not in models:
            models.append(model)
    return models[:16]


def _windows_static():
    result = {'os_name': 'Windows', 'kernel': None, 'cpu_model': None, 'gpu_models': []}
    try:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as opened:
                result['cpu_model'] = _text(winreg.QueryValueEx(opened, 'ProcessorNameString')[0])
        except OSError:
            pass
    except ImportError:
        pass
    try:
        version = sys.getwindowsversion()
        result['kernel'] = f'{version.major}.{version.minor}.{version.build}'
    except (AttributeError, OSError):
        pass
    try:
        class DisplayDevice(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_uint32), ('DeviceName', ctypes.c_wchar * 32), ('DeviceString', ctypes.c_wchar * 128), ('StateFlags', ctypes.c_uint32), ('DeviceID', ctypes.c_wchar * 128), ('DeviceKey', ctypes.c_wchar * 128)]
        enum = ctypes.windll.user32.EnumDisplayDevicesW
        enum.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.POINTER(DisplayDevice), ctypes.c_uint32]
        enum.restype = ctypes.c_int
        for index in range(32):
            device = DisplayDevice()
            device.cb = ctypes.sizeof(device)
            if not enum(None, index, ctypes.byref(device), 0):
                break
            model = _text(device.DeviceString)
            if model and not device.StateFlags & 8 and model not in result['gpu_models']:
                result['gpu_models'].append(model)
    except (AttributeError, OSError, ValueError):
        pass
    return result


def _architecture():
    try:
        if sys.platform != 'win32':
            return _text(os.uname().machine)
        kernel = ctypes.windll.kernel32
        handle = kernel.GetCurrentProcess
        handle.argtypes = []
        handle.restype = ctypes.c_void_p
        function = kernel.IsWow64Process2
        function.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint16)]
        function.restype = ctypes.c_int
        process, native = ctypes.c_uint16(), ctypes.c_uint16()
        if function(handle(), ctypes.byref(process), ctypes.byref(native)):
            name = {0x8664: 'x86_64', 0xAA64: 'ARM64', 0x014C: 'x86'}.get(native.value)
            if name:
                return name
    except (AttributeError, OSError, ValueError):
        pass
    return f'Python {struct.calcsize("P") * 8} bits (ISA não informada)'


def _hostname():
    try:
        return _text(socket.gethostname())
    except OSError:
        return None


def _static_info():
    kind = _container_kind()
    shared = kind == 'container'
    note = 'Resumo do ambiente do backend; não identifica automaticamente o alvo Ollama. Detecção de container por marcadores, sem garantia de isolamento.'
    if shared:
        note = 'Backend em container: SO pode ser da imagem; CPU e kernel podem ser compartilhados. Este resumo não identifica o host ou o alvo Ollama.'
    result = {
        'hostname': _hostname(),
        'environment': {'kind': kind, 'scope': 'backend_process', 'note': note},
        'os': {'name': None, 'kernel': None, 'architecture': _architecture()},
        'cpu': {'model': None, 'physical_cores': None, 'logical_cpus': None, 'scope': 'process_visible_shared_kernel' if shared else 'process_visible_not_exclusive'},
        'gpu': {'models': [], 'scope': 'container_visible' if shared else 'process_visible', 'note': 'Modelo não identificado ou dispositivo não exposto não significa ausência física de GPU; não indica uso pelo Ollama.'},
        'uptime_scope': 'shared_kernel' if shared else 'kernel',
    }
    if sys.platform == 'linux':
        result['os'].update(name=_linux_os(), kernel=_text(_read('/proc/sys/kernel/osrelease', 1024)))
        model, physical, logical = _linux_cpu()
        result['cpu'].update(model=model, physical_cores=physical, logical_cpus=logical)
        result['gpu']['models'] = _linux_gpus(kind)
    elif sys.platform == 'win32':
        windows = _windows_static()
        result['os'].update(name=windows['os_name'], kernel=windows['kernel'])
        result['cpu'].update(model=windows['cpu_model'], logical_cpus=os.cpu_count())
        result['gpu']['models'] = windows['gpu_models']
    return result


def _cgroup_memory():
    groups = _read('/proc/self/cgroup')
    candidates = []
    for line in groups.splitlines():
        parts = line.split(':', 2)
        if len(parts) != 3 or '..' in parts[2].split('/'):
            continue
        relative = parts[2].lstrip('/')
        if parts[:2] == ['0', '']:
            base = Path('/sys/fs/cgroup')
            leaf = base / relative
            while leaf != base and len(candidates) < 32:
                candidates.append((leaf, 'memory.max', 'memory.current'))
                leaf = leaf.parent
        elif 'memory' in parts[1].split(','):
            base = Path('/sys/fs/cgroup/memory')
            leaf = base / relative
            while leaf != base and len(candidates) < 32:
                candidates.append((leaf, 'memory.limit_in_bytes', 'memory.usage_in_bytes'))
                leaf = leaf.parent
    candidates.extend([(Path('/sys/fs/cgroup'), 'memory.max', 'memory.current'), (Path('/sys/fs/cgroup/memory'), 'memory.limit_in_bytes', 'memory.usage_in_bytes')])
    limits = []
    for base, limit_name, used_name in dict.fromkeys(candidates):
        limit = _read(base / limit_name, 128).strip()
        if not limit.isdigit():
            continue
        total = int(limit)
        if total >= 1 << 60:
            continue
        used = _read(base / used_name, 128).strip()
        usage = int(used) if used.isdigit() and int(used) <= total else None
        limits.append({'total_bytes': total, 'used_bytes': usage, 'available_bytes': total - usage if usage is not None else None, 'scope': 'cgroup_limit'})
    return min(limits, key=lambda item: item['total_bytes']) if limits else None


def _linux_memory(kind):
    constrained = _cgroup_memory()
    if constrained is not None:
        return constrained
    if kind == 'container':
        return {'total_bytes': None, 'used_bytes': None, 'available_bytes': None, 'scope': 'container_limit_unknown'}
    fields = {}
    for line in _read('/proc/meminfo').splitlines():
        match = re.fullmatch(r'(MemTotal|MemAvailable):\s*(\d+)\s+kB\s*', line)
        if match:
            fields[match[1]] = int(match[2]) * 1024
    total, available = fields.get('MemTotal'), fields.get('MemAvailable')
    if total is not None and available is not None and available > total:
        available = None
    return {'total_bytes': total, 'used_bytes': total - available if total is not None and available is not None else None, 'available_bytes': available, 'scope': 'system_memory'}


def _windows_memory(kernel32=None):
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('dwLength', ctypes.c_uint32), ('dwMemoryLoad', ctypes.c_uint32)] + [(name, ctypes.c_uint64) for name in ['ullTotalPhys', 'ullAvailPhys', 'ullTotalPageFile', 'ullAvailPageFile', 'ullTotalVirtual', 'ullAvailVirtual', 'ullAvailExtendedVirtual']]
    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(status)
    kernel32 = kernel32 if kernel32 is not None else ctypes.windll.kernel32
    function = kernel32.GlobalMemoryStatusEx
    function.argtypes = [ctypes.POINTER(MemoryStatus)]
    function.restype = ctypes.c_int
    if not function(ctypes.byref(status)):
        raise OSError('Memória não informada pelo sistema.')
    total, available = status.ullTotalPhys, status.ullAvailPhys
    if available > total:
        return {'total_bytes': total, 'used_bytes': None, 'available_bytes': None, 'scope': 'system_memory'}
    return {'total_bytes': total, 'used_bytes': total - available, 'available_bytes': available, 'scope': 'system_memory'}


def _windows_uptime(kernel32=None):
    kernel32 = kernel32 if kernel32 is not None else ctypes.windll.kernel32
    function = kernel32.GetTickCount64
    function.argtypes = []
    function.restype = ctypes.c_uint64
    return function() / 1000


def _dynamic_info(kind, app_path):
    memory = {'total_bytes': None, 'used_bytes': None, 'available_bytes': None, 'scope': 'unknown'}
    uptime = None
    if sys.platform == 'linux':
        memory = _linux_memory(kind)
        try:
            uptime = _number(float(_read('/proc/uptime', 1024).split()[0]))
        except (IndexError, ValueError):
            pass
    elif sys.platform == 'win32':
        if kind == 'container':
            memory['scope'] = 'container_limit_unknown'
        try:
            if kind != 'container':
                memory = _windows_memory()
        except (AttributeError, OSError, ValueError):
            pass
        try:
            uptime = _number(_windows_uptime())
        except (AttributeError, OSError, ValueError):
            pass
    disk = {'total_bytes': None, 'used_bytes': None, 'scope': 'app_filesystem'}
    try:
        values = shutil.disk_usage(app_path)
        disk.update(total_bytes=values.total, used_bytes=values.used)
    except OSError:
        pass
    return {'memory': memory, 'disk': disk, 'uptime_seconds': uptime}


class SystemCollector:
    """Cache static facts once and throttle dynamic reads without holding locks during I/O."""

    def __init__(self, static_source=None, dynamic_source=None, clock=None, utc_now=None, app_path=None):
        self._clock = clock or time.monotonic
        self._utc_now = utc_now or (lambda: datetime.now(timezone.utc).isoformat())
        self._lock = threading.Lock()
        self._last_attempt = None
        self._collecting = False
        self._failed = False
        self._cached = None
        try:
            source = (static_source or _static_info)()
        except Exception:
            source = {}
        if not isinstance(source, dict):
            source = {}
        environment, operating, cpu, gpu = (source.get(name) if isinstance(source.get(name), dict) else {} for name in ['environment', 'os', 'cpu', 'gpu'])
        kind = environment.get('kind')
        kind = kind if isinstance(kind, str) and kind in {'native', 'container', 'unknown'} else 'unknown'
        models = gpu.get('models') if isinstance(gpu.get('models'), list) else []
        self._static = {
            'collected_at': None,
            'hostname': _text(source.get('hostname')),
            'environment': {'kind': kind, 'scope': 'backend_process', 'note': _text(environment.get('note')) or 'Resumo do processo backend; informações indisponíveis não indicam ausência de hardware.'},
            'os': {key: _text(operating.get(key)) for key in ['name', 'kernel', 'architecture']},
            'cpu': {'model': _text(cpu.get('model')), 'physical_cores': _integer(cpu.get('physical_cores')), 'logical_cpus': _integer(cpu.get('logical_cpus')), 'scope': _text(cpu.get('scope')) or 'unknown'},
            'gpu': {'models': list(dict.fromkeys(filter(None, (_text(model) for model in models if isinstance(model, str)))))[:16], 'scope': _text(gpu.get('scope')) or 'unknown', 'note': _text(gpu.get('note')) or 'Modelo não identificado ou não exposto não indica ausência física de GPU.'},
            'memory': {'total_bytes': None, 'used_bytes': None, 'available_bytes': None, 'scope': 'unknown'},
            'disk': {'total_bytes': None, 'used_bytes': None, 'scope': 'app_filesystem'},
            'uptime_seconds': None,
            'uptime_scope': _text(source.get('uptime_scope')) or 'unknown',
        }
        location = app_path or Path(__file__).resolve().parent.parent
        self._dynamic_source = dynamic_source or (lambda: _dynamic_info(kind, location))

    def _result(self, busy):
        result = copy.deepcopy(self._cached or self._static)
        result['refresh'] = {'min_interval_s': 10, 'paused': busy, 'stale': busy or self._collecting or self._failed or self._cached is None}
        return result

    def snapshot(self, busy=False):
        with self._lock:
            now = self._clock()
            if busy or self._collecting or (self._last_attempt is not None and now - self._last_attempt < 10):
                return self._result(bool(busy))
            self._last_attempt = now
            self._collecting = True
        try:
            values = self._dynamic_source()
            result = copy.deepcopy(self._static)
            for name, keys in [('memory', ['total_bytes', 'used_bytes', 'available_bytes']), ('disk', ['total_bytes', 'used_bytes'])]:
                section = values.get(name, {})
                result[name].update({key: _integer(section.get(key)) for key in keys})
                if name == 'memory':
                    result[name]['scope'] = _text(section.get('scope')) or 'unknown'
                total = result[name]['total_bytes']
                if total is not None and result[name]['used_bytes'] is not None and result[name]['used_bytes'] > total:
                    result[name]['used_bytes'] = None
                if name == 'memory' and total is not None and result[name]['available_bytes'] is not None and result[name]['available_bytes'] > total:
                    result[name]['available_bytes'] = None
            result['uptime_seconds'] = _number(values.get('uptime_seconds'))
            result['collected_at'] = self._utc_now()
        except Exception:
            with self._lock:
                self._collecting = False
                self._failed = True
                return self._result(False)
        with self._lock:
            self._cached = result
            self._collecting = self._failed = False
            return self._result(False)
