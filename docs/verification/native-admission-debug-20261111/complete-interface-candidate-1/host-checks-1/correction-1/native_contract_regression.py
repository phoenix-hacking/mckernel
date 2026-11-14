"""Four candidate-specific HOST checks; execution requires Root's admission.

Every SUT module is loaded whole from byte-pinned private copies. Only external
file/kernel/channel/process/backend effects are virtual. No real native, root,
service, account, controller, flag ioctl, process spawn, signal or VM is called.
The ordinary outer Owner remains real and is outside this test process.
"""
import base64
import builtins
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import struct
import sys
import types

HERE = Path(__file__).resolve().parent
INPUTS = json.loads((HERE / 'INPUTS.json').read_text())
assert sys.version_info[:2] == (3, 8), 'qualified HOST Python3.8 required'
GIB = 1024 ** 3
PACKAGE_NONCE = 'e' * 64
PACKAGE = '/var/lib/mckernel-code-' + PACKAGE_NONCE + '/installed-source-' + PACKAGE_NONCE
ROOT = '/test-only/current-operation'
NONCE = 'a' * 64
BOOT = 'test-only-current-boot'
CAP = 1570.0
ORIGINAL = ('ownership_latch', 'custody_protocol_v2', 'graph_observations',
            'pidfd_compat', 'runtime_binding', 'pidfd_custody', 'deferred_fork',
            'inplace_custody', 'immutable_epoch', 'adapter', 'materializer',
            'source_freeze', 'split_inventory', 'union_server_guarded',
            'graph_producer', 'graph_server', 'operation_supervisor', 'supervisor_entry')
NAMED = ('native_current_owner', 'native_diagnostic_container_owner',
         'native_resource_admission', 'native_source_binding', 'compositor',
         'operation_watchdog')
EXTRAS = ('verify_scripts_fd', 'verified_owner_loader', 'union_owner', 'root_owner_entry')
LOADED = ('ownership_latch', 'custody_protocol_v2', 'inplace_custody',
          'immutable_epoch', 'root_bootstrap', 'native_resource_admission',
          'native_source_binding', 'compositor', 'operation_watchdog',
          'native_diagnostic_container_owner')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(row):
    raw = Path(row['path']).read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    return raw


def reject(function, text):
    try:
        function()
    except (RuntimeError, ValueError, TimeoutError, AssertionError) as error:
        assert text in str(error), (text, type(error).__name__, str(error))
        return
    raise AssertionError('expected refusal: ' + text)


class Clock:
    CLOCK_BOOTTIME = 7
    def __init__(self): self.now = 1000.0
    def time(self): return self.now
    def monotonic(self): return self.now
    def clock_gettime(self, which):
        assert which == self.CLOCK_BOOTTIME
        return self.now
    def sleep(self, seconds): raise AssertionError('no actual sleeping in controlled checks')


class VirtualFS:
    """Finite lower filesystem/kernel model: never falls back to the real OS."""
    def __init__(self):
        self.files = {}; self.handles = {}; self.next_fd = 1000
        self.events = []; self.closed = []; self.close_fail = set()
        self.locked = True; self.pid = 4001; self.lock_pid = 4001
        self.kernel = {}; self.memory = 26 * GIB
        self.free = {'/home/holden/mckernel': 16 * GIB,
                     '/home/holden/mckernel-work/scratch': 12 * GIB}
        self.waits = []; self.wait_result = None
        self.on_fsync = None
        self.add('/', b'', directory=True, mode=0o755)
        self.add('/proc/self/ns/mnt', b'', mode=0o444)
        self.namespace = (self.files['/proc/self/ns/mnt']['st'].st_dev,
                          self.files['/proc/self/ns/mnt']['st'].st_ino)
        self.mounts = {'/': {'id': 1, 'device': '8:1', 'root': '/', 'options': 'rw'}}

    def add(self, path, raw, directory=False, mode=0o644, flags=0):
        path = str(path)
        if path in self.files:
            self.files[path]['raw'] = bytearray(raw)
            self.files[path]['st'].st_size = len(raw)
            return
        parent = str(Path(path).parent)
        if parent != path and parent not in self.files:
            self.add(parent, b'', directory=True, mode=0o755)
        inode = 100 + len(self.files)
        st = types.SimpleNamespace(st_dev=os.makedev(8, 1), st_ino=inode,
             st_uid=0, st_gid=0, st_nlink=1,
             st_mode=(stat.S_IFDIR if directory else stat.S_IFREG) | mode,
             st_size=len(raw), st_mtime_ns=1, st_ctime_ns=1)
        self.files[path] = dict(raw=bytearray(raw), st=st, flags=flags)

    def path(self, name, dir_fd=None):
        name = str(name)
        if not name.startswith('/'):
            assert dir_fd in self.handles, 'only virtual dirfds allowed'
            name = self.handles[dir_fd]['path'].rstrip('/') + '/' + name
        return name

    def open(self, name, flags, mode=0o600, dir_fd=None):
        path = self.path(name, dir_fd)
        if flags & os.O_CREAT:
            if flags & os.O_EXCL and path in self.files: raise FileExistsError(path)
            if path not in self.files: self.add(path, b'', mode=mode)
        assert path in self.files, 'unmodeled file access: ' + path
        fd = self.next_fd; self.next_fd += 1
        self.handles[fd] = dict(path=path, position=0)
        self.events.append(('open', fd, path))
        return fd

    def fstat(self, fd):
        assert fd in self.handles, ('not a virtual fd', fd)
        return self.files[self.handles[fd]['path']]['st']

    def close(self, fd):
        assert fd in self.handles, ('unowned close', fd)
        self.closed.append(fd); self.events.append(('close', fd))
        if fd in self.close_fail: raise OSError('test-only uncertain close')
        del self.handles[fd]

    def read(self, fd, count):
        h = self.handles[fd]; raw = self.files[h['path']]['raw']
        out = bytes(raw[h['position']:h['position'] + count]); h['position'] += len(out)
        return out

    def write(self, fd, raw):
        path = self.handles[fd]['path']; self.files[path]['raw'].extend(raw)
        self.files[path]['st'].st_size = len(self.files[path]['raw'])
        self.events.append(('write', path, bytes(raw)))
        return len(raw)

    def fsync(self, fd):
        assert fd in self.handles
        self.events.append(('fsync', self.handles[fd]['path']))
        if self.on_fsync is not None: self.on_fsync(self.handles[fd]['path'])

    def stat(self, name, dir_fd=None, follow_symlinks=False):
        path = self.path(name, dir_fd)
        assert path in self.files, path
        return self.files[path]['st']

    def listdir(self, fd):
        path = self.handles[fd]['path'].rstrip('/') + '/'
        return [p[len(path):] for p in self.files
                if p.startswith(path) and '/' not in p[len(path):] and p != path]

    def pin(self, path, digest, limit=2 * 1024 * 1024):
        assert path in self.files, path
        raw = bytes(self.files[path]['raw'])
        assert len(raw) <= limit and sha(raw) == digest, 'controlled pinned bytes mismatch'
        return self.open(path, os.O_RDONLY), raw

    def ioctl(self, fd, operation, data, mutate=False):
        row = self.files[self.handles[fd]['path']]
        if operation == 0x80086601:
            data[:] = struct.pack('I', row['flags']); return 0
        assert operation == 0x40086602, 'only virtual immutable flags operation'
        value = struct.unpack('I', data)[0]
        self.events.append(('ioctl', self.handles[fd]['path'], value))
        row['flags'] = value
        return 0

    def flock(self, fd, operation):
        assert self.handles[fd]['path'] == '/test-only/development.lock'
        self.events.append(('flock', fd, operation))
        assert operation == 8, 'only current release is tested'
        self.locked = False

    def read_text(self, path):
        if path == '/proc/sys/kernel/random/boot_id': return BOOT
        if path == '/proc/meminfo': return 'MemAvailable: %d kB\n' % (self.memory // 1024)
        if path == '/proc/locks':
            if not self.locked: return ''
            s = self.files['/test-only/development.lock']['st']
            return '1: FLOCK ADVISORY WRITE %d %02x:%02x:%d 0 EOF\n' % (
                self.lock_pid, os.major(s.st_dev), os.minor(s.st_dev), s.st_ino)
        assert path in self.files, 'unmodeled path read: ' + path
        return bytes(self.files[path]['raw']).decode()

    def path_type(self):
        fs = self
        class ControlledPath:
            def __init__(self, path): self.value = Path(path)
            def __str__(self): return str(self.value)
            def __fspath__(self): return str(self.value)
            @property
            def name(self): return self.value.name
            def with_name(self, value): return ControlledPath(self.value.with_name(value))
            def read_text(self): return fs.read_text(str(self.value))
            def read_bytes(self): return bytes(fs.files[str(self.value)]['raw'])
        return ControlledPath

    def os_type(self):
        fs = self
        class ControlledOS:
            path = os.path
            environ = {}
            def __getattr__(self, name):
                if name.startswith('O_') or name in ('WNOHANG',): return getattr(os, name)
                if name in ('major', 'minor', 'WIFEXITED', 'WEXITSTATUS'): return getattr(os, name)
                raise AssertionError('unmodeled OS effect: ' + name)
            def getuid(self): return 0
            def geteuid(self): return 0
            def getpid(self): return fs.pid
            def getppid(self): return 3001
            def open(self, *a, **k): return fs.open(*a, **k)
            def close(self, fd): return fs.close(fd)
            def read(self, *a): return fs.read(*a)
            def write(self, *a): return fs.write(*a)
            def fsync(self, fd): return fs.fsync(fd)
            def fstat(self, fd): return fs.fstat(fd)
            def stat(self, *a, **k): return fs.stat(*a, **k)
            def lstat(self, name): return fs.stat(name)
            def listdir(self, fd): return fs.listdir(fd)
            def statvfs(self, path):
                assert path in fs.free
                return types.SimpleNamespace(f_bavail=fs.free[path], f_frsize=1)
            def getxattr(self, *a):
                import errno
                raise OSError(errno.ENODATA, 'test-only no ACL')
            def set_blocking(self, fd, value): assert fd in fs.handles and value is False
            def waitpid(self, pid, options):
                fs.waits.append((pid, options))
                assert fs.wait_result is not None and fs.wait_result[0] == pid
                return fs.wait_result
        return ControlledOS()


class Client:
    def __init__(self): self.closed = 0; self.calls = 0; self.revoked = False; self.effect = None
    def revalidate(self):
        self.calls += 1
        if self.effect is not None: self.effect()
        if self.revoked: raise RuntimeError('test-only current controller veto')
        return {'authority': None, 'native_grant': False}
    def close(self): self.closed += 1


class Environment:
    def __init__(self):
        self.fs = VirtualFS(); self.clock = Clock(); self.modules = {}; self.raw = {}
        self.sig = types.ModuleType('signal')
        for name in ('SIG_BLOCK', 'SIG_SETMASK', 'SIGINT', 'SIGTERM', 'SIGHUP', 'SIGKILL'):
            setattr(self.sig, name, getattr(signal, name))
        self.sig.SIG_IGN = signal.SIG_IGN
        self.sig.getsignal = lambda number: 'test-only prior handler'
        self.sig.signal = lambda number, handler: None
        self.sig.pthread_sigmask = lambda how, mask: set()
        actual_import = builtins.__import__
        def controlled_import(name, *a, **k):
            return self.sig if name == 'signal' else actual_import(name, *a, **k)
        safe_builtins = dict(vars(builtins)); safe_builtins['__import__'] = controlled_import
        for name, row in INPUTS['package_sources'].items():
            self.raw[name] = checked(row)
            module = types.ModuleType(name); module.__file__ = PACKAGE + '/' + name + '.py'
            self.modules[name] = module; sys.modules[name] = module
            module.__dict__['__builtins__'] = safe_builtins
        obs = self.modules['graph_observations']
        obs.canonical = canonical
        obs.stable = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid,
                                s.st_nlink, s.st_size, s.st_mtime_ns)
        obs.process = lambda pid: ('9000' if pid == self.fs.pid else '9001',) + self.fs.namespace
        obs.read_mountinfo = lambda pid, process: self.fs.mounts.copy()
        obs.file_sha = lambda path: sha(bytes(self.fs.files[path]['raw']))
        obs.direct_path = lambda path: (self.fs.files[path]['st'], None)
        runtime = self.modules['runtime_binding']
        runtime.verify_current = lambda path, digest: self.fs.pin(path, digest)[0]
        current = self.modules['native_current_owner']
        def unique(pairs):
            result = {}
            for key, value in pairs:
                assert key not in result, 'duplicate controlled JSON key'
                result[key] = value
            return result
        current.unique = unique
        current.birth = lambda pid: '9000' if pid == self.fs.pid else '9001'
        class ChannelCleanupError(RuntimeError):
            def __init__(self, primary, secondary): super().__init__('controlled closure unknown'); self.secondary = secondary
        current.ChannelCleanupError = ChannelCleanupError
        for name in LOADED:
            module = self.modules[name]
            exec(compile(self.raw[name], INPUTS['package_sources'][name]['origin'], 'exec'), module.__dict__)
            module.os = self.fs.os_type(); module.time = self.clock
            module.fcntl = types.SimpleNamespace(ioctl=self.fs.ioctl, flock=self.fs.flock,
                          LOCK_UN=8, LOCK_EX=2, LOCK_NB=4)
            if 'Path' in module.__dict__: module.Path = self.fs.path_type()
        self.native = self.modules['native_resource_admission']
        self.source = self.modules['native_source_binding']
        self.inplace = self.modules['inplace_custody']
        self.comp = self.modules['compositor']; self.watch = self.modules['operation_watchdog']
        self.root = self.modules['root_bootstrap']; self.owner_module = self.modules['native_diagnostic_container_owner']
        self.real_owner_class = self.owner_module.DiagnosticOwner
        self.root.pinned_root_file = self.fs.pin
        graph = self.modules['graph_producer']; graph.wire = self.modules['custody_protocol_v2']
        env = self
        class ControlledLease:
            def __init__(self):
                self.root_fd = env.root_fd; self.nonce = NONCE; self.lease_sha256 = 'b' * 64
                self.revoked = False
            def verify(self):
                if self.revoked: raise RuntimeError('test-only inherited lease veto')
        graph.RootLease = ControlledLease
        self.fs.add(ROOT, b'', directory=True, mode=0o700)
        self.root_fd = self.fs.open(ROOT, os.O_RDONLY)
        self.fs.add(PACKAGE, b'', directory=True, mode=0o755, flags=0x10)
        for name, raw in self.raw.items(): self.fs.add(PACKAGE + '/' + name + '.py', raw, flags=0x10)
        self.fs.add('/test-only/python', b'test-only runtime', flags=0x10)
        self.fs.add('/test-only/development.lock', b'', mode=0o600)
        self.fs.add('/test-only/scope.json', checked(INPUTS['retained_scope']), flags=0x10)
        self.fs.add('/test-only/manifest.json', b'{}', flags=0x10)
        self.lease = ControlledLease()
        self.cfg = dict(kind=self.native.KIND, nonce=NONCE, boot_id=BOOT,
            caps=dict(utc=CAP, boot=CAP, mono=CAP, boot_id=BOOT),
            watchdog_pid=self.fs.pid, watchdog_birth='9000',
            runtime=dict(path='/test-only/python', sha256=sha(b'test-only runtime')),
            owner=dict(path=PACKAGE + '/native_diagnostic_container_owner.py',
                       sha256=sha(self.raw['native_diagnostic_container_owner'])),
            operation_root=self.native.file_identity(self.root_fd),
            native=dict(manifest=dict(path='/test-only/manifest.json', sha256=sha(b'{}')),
              attempt_parent=self.owner_module.SCRATCH + '/test-only/native-attempt',
              source_manifest=dict(path='/test-only/source-manifest.json', sha256='0' * 64),
              source_package=dict(path=PACKAGE, device=self.fs.files[PACKAGE]['st'].st_dev,
                inode=self.fs.files[PACKAGE]['st'].st_ino, uid=0, mode=0o755),
              profile=dict(cpus=[2,3,4,5], memory_bytes=12*GIB, memory_swap_bytes=12*GIB,
                           pids=512, network='none', heavy_jobs=1),
              scope=dict(path='/test-only/scope.json', sha256=self.native.VerifiedResourceScope.FACTS_SHA),
              controller=dict(path='/test-only/controller.sock', pid=3001, birth='9001', source_sha256='c'*64),
              deadline_seconds=360))
        self.save_request()
        self.native.read_kernel = self.read_kernel
        self.fs.kernel.update(self.native.CGROUP)
        self.fs.kernel.update({p: '' for p in self.native.MEMBERS})
        self.fs.kernel['/sys/fs/cgroup/memory/mckernel-dev/memory.usage_in_bytes'] = '0'
        self.fs.kernel['/sys/fs/cgroup/pids/mckernel-dev/pids.current'] = '0'

    def save_request(self):
        raw = canonical(self.cfg)
        self.fs.add('/test-only/operation.json', raw, mode=0o600, flags=0x10)
        self.request = self.native.VerifiedNativeRequest('/test-only/operation.json', sha(raw))

    def read_kernel(self, path):
        assert path in self.fs.kernel, 'missing controlled kernel input: ' + path
        return self.fs.kernel[path]

    def admission(self):
        n = self.native; a = n.NativeAdmission.__new__(n.NativeAdmission)
        a.state = 'CLAIMED'; a.root_fd = self.root_fd; a.lease = self.lease
        a.request = self.request; a.cfg = self.cfg; a.nonce = NONCE
        a.config_sha = self.request.sha256; a.caps = dict(self.cfg['caps']); a.boot_id = BOOT
        a.deadline_seconds = self.cfg['native']['deadline_seconds']
        a.client = Client(); a.failure = None; a.completion = None
        a.resource_scope = n.VerifiedResourceScope(self.cfg['native']['scope'], self.request)
        a.package_fd = self.fs.open(PACKAGE, os.O_RDONLY)
        a.development_fd = self.fs.open('/test-only/development.lock', os.O_RDONLY)
        a.development_identity = n.file_identity(a.development_fd)
        a.loader_fds = []; a.source_members = []; a.open_fds = []
        a.claim_fd = self.fs.open('claim.jsonl', os.O_WRONLY | os.O_CREAT | os.O_EXCL, dir_fd=self.root_fd)
        a.owner_module = self.owner_module; a.retained = {'lower_effects_only': True}
        return a

    def loader(self):
        value = dict(kind='mckernel-native-signal-loader-v1',
            modules={name: dict(path=PACKAGE + '/' + name + '.py', sha256=sha(self.raw[name]))
                     for name in ORIGINAL + NAMED},
            extra_files={PACKAGE + '/' + name + '.py': sha(self.raw[name]) for name in EXTRAS},
            operation_config_path=self.request.path, operation_config_sha=self.request.sha256,
            runtime=dict(self.cfg['runtime']))
        self.fs.add('/test-only/loader.json', canonical(value), flags=0x10)
        return value

    def bind_owner(self, admission):
        env = self; module = self.owner_module
        manifest = dict(artifacts={name: dict(path=module.SCRATCH + '/test-only/' + name,
                             sha256='d'*64) for name in self.native.EXPECTED},
                        modules=[dict(path=module.SCRATCH + '/test-only/module' + str(i), sha256=value)
                                 for i, value in enumerate(self.native.MODULES)])
        class LowerDiagnosticOwner:
            def __init__(self, parent, manifest, manifest_sha256, nonce):
                self.parent = Path(parent); self.manifest_path = manifest
                self.manifest_sha256 = manifest_sha256; self.manifest = env.manifest
                self.container = 'e' * 64; self.cleaning = False; self.calls = []
                self.nonce = nonce; self.name = 'test-only-diagnostic-' + nonce
                self.label = 'mckernel.native-diagnostic.owner=' + nonce
                self.owner_sha = sha(env.raw['native_diagnostic_container_owner'])
                self.lock = admission.development_fd; self.absent = False
                self.create_issued = True; self.create_completed = True; self.failure = None
                self.backend = module.DockerBackend()
            def _profile(self, row, image): self.calls.append(('profile', row['State']['Status']))
            def _call(self, argv, *args, **kwargs):
                self.calls.append(('call', list(argv)))
                self.last_call_args = tuple(args)
                self.last_call_kwargs = dict(kwargs)
                return {'controlled_lower_call': list(argv)}
            def run(self, *args, **kwargs):
                self.run_arguments = (args, kwargs)
                self.absent = True; self.lock = None
            def _remember(self, error): self.failure = error
            _inside_args = env.real_owner_class._inside_args
        self.manifest = manifest
        module.DiagnosticOwner = LowerDiagnosticOwner
        module.bound_manifest = lambda path, digest: (None, self.manifest)
        ref = dict(path=module.SCRATCH + '/test-only/manifest.json', sha256=sha(canonical(manifest)))
        self.fs.add(ref['path'], canonical(manifest))
        admission.cfg['native']['manifest'] = ref
        # This decoded fixture request is repinned before any SUT verification.
        self.save_request(); admission.request = self.request; admission.config_sha = self.request.sha256
        admission.resource_scope.request = self.request
        owner = self.native._bound_owner(module, admission, self.cfg['native']['attempt_parent'], ref)
        admission.owner = owner
        return owner

    def held_source(self, before_acquire=None, omit_from_cut=None):
        a = self.admission(); owner = self.bind_owner(a)
        source_paths = {PACKAGE + '/' + name + '.py' for name in ORIGINAL + NAMED + EXTRAS}
        source_paths.add(PACKAGE + '/root_bootstrap.py')
        a.source_members = sorted(source_paths)
        required = set(a.source_members) | set(owner.admitted_source_paths) | {owner.manifest_path}
        required.update(ref['path'] for ref in self.manifest['artifacts'].values())
        required.update(ref['path'] for ref in self.manifest['modules'])
        if omit_from_cut is not None:
            assert omit_from_cut in a.source_members and omit_from_cut in required
            required.remove(omit_from_cut)
        for path in sorted(required):
            if path not in self.fs.files: self.fs.add(path, ('test-only consumed lower data:' + path).encode())
        rows = [dict(target=p, host=p, content_sha256=sha(bytes(self.fs.files[p]['raw']))) for p in sorted(required)]
        # Include both preexisting and newly added immutable bits.
        self.added_path = self.manifest['artifacts']['payload']['path']
        self.fs.files[self.added_path]['flags'] = 0x20
        plan = {p: [self.fs.files[p]['st'].st_dev, self.fs.files[p]['st'].st_ino,
                    stat.S_IFMT(self.fs.files[p]['st'].st_mode), self.fs.files[p]['flags']]
                for p in sorted(required)}
        roots = {p: dict(mountpoint='/', **self.fs.mounts['/']) for p in sorted(required)}
        manifest = dict(sources=rows, inode_plan_sha256=sha(canonical(plan)),
                        mount_map_sha256=sha(canonical(dict(namespace=list(self.fs.namespace), roots=roots))))
        self.fs.add('/test-only/source-manifest.json', canonical(manifest), mode=0o600, flags=0x10)
        self.cfg['native']['source_manifest'] = dict(path='/test-only/source-manifest.json', sha256=sha(canonical(manifest)))
        self.save_request(); a.request = self.request; a.config_sha = self.request.sha256
        a.resource_scope.request = self.request
        source = self.source.NativeSourceCustody(a)
        if before_acquire is not None: before_acquire(a, source)
        source.acquire(); a.source_held(source)
        custody = types.SimpleNamespace(native_admission=a, state='NATIVE_SOURCE_HELD')
        a.plan = self.comp.NativeSourcePlan(custody, a, source)
        self.comp._accept_source_binding(a.plan)
        return a, source, owner

    def inspect(self, owner):
        binds = [(owner.owner_repo, True), (owner.owner_scratch, True),
                 (str(owner.parent), False), (owner.source_package, True)]
        return dict(Id=owner.container, Image=owner.owner_image,
             State=dict(Status='created', Running=False),
             Mounts=[dict(Type='bind', Source=p, Destination=p, RW=not ro,
                          Propagation='rprivate') for p, ro in binds] +
                    [dict(Type='tmpfs', Destination='/tmp', RW=True)])


def registered_context():
    e = Environment(); n = e.native; a = e.admission(); loader = e.loader()
    bootstrap = e.raw['root_bootstrap']; raw_loader = canonical(loader)
    n.sys.argv = ['-c', base64.b64encode(bootstrap).decode(), '/test-only/loader.json',
                  sha(raw_loader), loader['modules']['supervisor_entry']['path']]
    a._registered_loader()
    assert len(a.source_members) == 29 and len(a.loader_fds) == 30
    launched = []
    old_launch = e.watch.launch_reviewed
    e.watch.launch_reviewed = lambda *args, **kwargs: launched.append((args, kwargs)) or types.SimpleNamespace()
    e.root.load_verified_module = lambda name, path, digest: (e.fs.pin(path, digest)[0], e.modules[name])
    watchdog = e.root.launch_named_native_from_registered_loader(PACKAGE + '/root_bootstrap.py', sha(bootstrap),
        '/test-only/loader.json', sha(raw_loader), e.root_fd, {'PATH': '/usr/bin:/bin'}, 2)
    assert len(launched) == 1 and type(launched[0][1]['native_request']) is n.VerifiedNativeRequest
    assert len(watchdog.source_loader_holds) == 30
    e.watch.launch_reviewed = old_launch
    e.modules['materializer'].__file__ = PACKAGE + '/wrong-origin.py'
    reject(a._registered_loader, 'actual verified module origin differs')
    e.modules['materializer'].__file__ = loader['modules']['materializer']['path']
    old_modules = loader['modules']; loader['modules'] = {k: v for k, v in old_modules.items() if k in ORIGINAL}
    e.fs.add('/test-only/loader.json', canonical(loader))
    n.sys.argv[3] = sha(canonical(loader))
    reject(a._registered_loader, 'complete actual original18 plus named dependencies required')
    reject(lambda: e.comp._collect({}, {}), 'authenticated source and effective-view release unbound')
    reject(lambda: n.NativeAdmission(e.root_fd, e.lease, {}, e.owner_module), 'root-pinned typed native request required')
    e.request.cfg['watchdog_birth'] = '9999'
    reject(e.request.verify, 'decoded fields changed')
    e.request.cfg['watchdog_birth'] = '9000'
    e.clock.now = CAP
    reject(e.request.verify, 'expired or unbounded')
    # Corrected source must recheck caps after a potentially blocking revalidation.
    e = Environment(); a = e.admission(); e.bind_owner(a)
    a.client.effect = lambda: setattr(e.clock, 'now', CAP + 1)
    reject(lambda: a.owner._call(['create']), 'expired or unbounded')
    assert not a.owner.calls, 'late revocation must refuse before the lower command/Popen boundary'
    e = Environment(); a, source, owner = e.held_source()
    argv = e.real_owner_class._create_argv(owner)
    assert argv.count('type=bind,src=' + PACKAGE + ',dst=' + PACKAGE + ',readonly') == 1
    assert argv.count('--mount') == 4
    completion = a.launch(source)
    assert type(completion) is e.native.NativeCompletion
    assert owner.run_arguments == ((), {'deadline': 360}), 'declared duration must reach actual owner.run'
    assert e.native.COMPLETION_RESERVE_SECONDS == 69 and e.native.RETIREMENT_RESERVE_SECONDS == 24
    for value in (True, 360.0, 359):
        bad = Environment(); bad.cfg['watchdog_pid'] = 3001; bad.cfg['watchdog_birth'] = '9001'
        bad.cfg['native']['deadline_seconds'] = value; bad.save_request()
        reject(lambda: bad.native.NativeAdmission(bad.root_fd, bad.lease, bad.request, bad.owner_module),
               'exact supported native owner duration360 required')
    e = Environment(); a, source, owner = e.held_source(); owner._profile(e.inspect(owner), {})
    e.clock.now = CAP - 428
    before = len(owner.calls)
    reject(lambda: owner._call(['start', owner.container], timeout=360), 'clock/work allowance')
    reject(lambda: a.launch(source), 'clock/work allowance')
    assert len(owner.calls) == before
    e.clock.now = CAP - 429
    assert a.work_timeout(360, start=True) == 360, 'exact429s start budget is sufficient'
    e = Environment(); a = e.admission(); owner = e.bind_owner(a); e.clock.now = CAP - 30
    owner._call(['inspect', owner.container], timeout=90)
    assert owner.last_call_kwargs['timeout'] == 6.0, '30 remaining minus24 reserve clips to6'
    e.clock.now = CAP - 24
    reject(lambda: owner._call(['inspect', owner.container], timeout=1), 'work allowance exhausted')
    e.clock.now = CAP - 23
    reject(lambda: owner._call(['inspect', owner.container], timeout=1), 'clock/work allowance')
    for bad_path in (PACKAGE.replace('installed-source-' + PACKAGE_NONCE, 'installed-source-' + 'f'*64),
                     PACKAGE + '/extra', '/var/lib/mckernel-native-test-only/source'):
        assert not e.owner_module.normal_source_generation(bad_path)
        owner.source_package = bad_path
        reject(lambda: e.real_owner_class._create_argv(owner), 'named immutable package source')
    bad = Environment(); bad.cfg['watchdog_pid'] = 3001; bad.cfg['watchdog_birth'] = '9001'
    bad.cfg['native']['source_package']['path'] = PACKAGE + '/extra'; bad.save_request()
    reject(lambda: bad.native.NativeAdmission(bad.root_fd, bad.lease, bad.request, bad.owner_module),
           'named immutable package path')
    # Let durable prior-flags I/O consume the cap. Actual acquire/apply_plan and
    # NativeWorkLatch must retain UNKNOWN without publishing even one new bit.
    e = Environment(); held = {}
    def before_acquire(admission, cut):
        held.update(admission=admission, source=cut)
        def after_fsync(path):
            if cut.journal is None: return
            if path != e.fs.handles[cut.journal]['path']: return
            rows = [json.loads(line) for line in bytes(e.fs.files[path]['raw']).splitlines()]
            if rows and 'old_flags' in rows[-1] and not rows[-1]['old_flags'] & 0x10:
                e.clock.now = CAP + 1
        e.fs.on_fsync = after_fsync
    reject(lambda: e.held_source(before_acquire), 'expired or unbounded')
    assert held['source'].state == held['admission'].state == 'UNKNOWN_RETAINED'
    assert not [event for event in e.fs.events if event[0] == 'ioctl']
    return dict(registered_members=29, held_loader_fds=30, typed_request=True,
                old_graph_refused=True, late_revalidation_precommand_refused=True,
                declared_owner_seconds=360, start_window_seconds=429,
                ordinary_reserve_seconds=24, clipped_timeout_seconds=6,
                normal_same_nonce_generation_required=True,
                late_source_publication_refused=True)


def capacity_claim():
    e = Environment(); n = e.native; a = e.admission(); scope = a.resource_scope
    assert scope.required_bytes == 26 * GIB
    facts = scope.value['source_input_facts_for_actual_native_admission']
    assert facts['retained_total_bytes'] == 18 * GIB
    assert facts['R3_memory_row']['current_process_charge_bytes'] == 0
    assert len(facts['persistent_nonmemory_UNKNOWN_rows']) == 4
    a._capacity(); a.verify(); n.physical_snapshot(True)
    e.fs.memory -= 1024
    reject(a._capacity, 'actual shared/native memory headroom')
    e.fs.memory += 1024; e.fs.free['/home/holden/mckernel-work/scratch'] -= 1
    reject(a._capacity, 'actual host/scratch floor')
    e.fs.free['/home/holden/mckernel-work/scratch'] += 1
    member = n.MEMBERS[0]; e.fs.kernel[member] = '6101'
    reject(lambda: n.physical_snapshot(True), 'not positively idle')
    e.fs.kernel[member] = ''
    key = '/sys/fs/cgroup/pids/mckernel-dev/pids.current'; del e.fs.kernel[key]
    reject(lambda: n.physical_snapshot(True), 'missing controlled kernel input')
    e.fs.kernel[key] = '0'
    e.fs.locked = False
    a.client.revalidate = lambda: {'approved': True, 'native_grant': True, 'capacity': 12 * GIB}
    reject(a.verify, 'actual current native development-lock owner differs')
    e.fs.locked = True
    e.fs.lock_pid = 6001
    reject(a.verify, 'actual current native development-lock owner differs')
    e.fs.lock_pid = e.fs.pid
    a.client.revoked = True
    a.client.revalidate = Client.revalidate.__get__(a.client, Client)
    reject(a.verify, 'test-only current controller veto')
    # Cleanup keeps physical/source/FLOCK checks but does not grant further work.
    a.verify(cleanup=True)
    return dict(retained_bytes=18*GIB, fresh_bytes=26*GIB, R3_process_bytes=0,
                persistent_outcomes=4, static_or_account_data_not_claim=True,
                readable_kernel_and_current_flock_required=True)


def effective_source():
    e = Environment(); a, source, owner = e.held_source()
    journal_path = e.fs.handles[source.journal]['path']
    events = [json.loads(line) for line in bytes(e.fs.files[journal_path]['raw']).splitlines()]
    prior = [row for row in events if set(row) == {'path', 'device', 'inode', 'old_flags'}]
    assert len(prior) == len(source.rows) and len({row['path'] for row in prior}) == len(prior)
    for position, event in enumerate(e.fs.events):
        if event[0] != 'ioctl': continue
        path = event[1]
        matching = [i for i, row in enumerate(e.fs.events[:position])
                    if row[0] == 'write' and row[1] == journal_path and
                    json.loads(row[2]).get('path') == path and 'old_flags' in json.loads(row[2])]
        assert len(matching) == 1
        assert any(row == ('fsync', journal_path) for row in e.fs.events[matching[0]+1:position])
    collection = json.loads(e.comp._collect(a.plan))
    assert collection['authority'] is None and len(a.source_members) == 29
    reject(lambda: owner._call(['start', owner.container]), 'actual source/effective view required')
    assert not [row for row in owner.calls if row[0] == 'call']
    wrong = e.inspect(owner); wrong['Mounts'][0]['RW'] = True
    reject(lambda: owner._profile(wrong, {}), 'actual exact four native binds differ')
    assert source.effective is None
    wrong = e.inspect(owner); wrong['Mounts'][3]['Destination'] = PACKAGE + '-wrong-target'
    reject(lambda: owner._profile(wrong, {}), 'actual exact four native binds differ')
    owner._profile(e.inspect(owner), {})
    assert a.plan.effective_accepted and source.effective['root_only_sources'] == [e.owner_module.IMAGE_RECORD]
    result = owner._call(['start', owner.container])
    assert result['controlled_lower_call'] == ['start', owner.container]
    before = len(owner.calls); a.client.revoked = True
    reject(lambda: owner._call(['start', owner.container]), 'test-only current controller veto')
    assert len(owner.calls) == before
    # Build a coherent source manifest/plan/epoch missing one real consumed
    # member. Do not corrupt a held cut's descriptor-to-row invariant.
    omitted = Environment(); missing = PACKAGE + '/adapter.py'
    omitted_admission, omitted_source, _ = omitted.held_source(omit_from_cut=missing)
    assert missing in omitted_admission.source_members and missing not in omitted_source.fds
    assert all(row['host'] in omitted_source.fds for row in omitted_source.rows)
    reject(omitted_source.collect, 'consumed diagnostic source/artifact file omitted')
    return dict(registered_source_members=29, durable_unique_prior_flags=True,
                all_consumed_files_required=True, four_actual_binds_required=True,
                host_only_image_record=True, start_after_effective_acceptance=True,
                revoked_start_did_not_reach_lower_effect=True)


def prepare_parent_records(e, a, source, owner):
    n = e.native; fd = a.development_fd; identity = n.file_identity(fd)
    parent_request = n.VerifiedNativeRequest(e.request.path, e.request.sha256)
    completion = a.launch(source)
    assert type(completion) is n.NativeCompletion and a.state == 'TERMINAL_CLEAN'
    original = dict(source.plan)
    source.restore(completion)
    assert all(e.fs.files[p]['flags'] == values[3] for p, values in original.items())
    assert e.fs.files[PACKAGE + '/root_bootstrap.py']['flags'] & 0x10
    source.close_restored(); assert source.state == 'CLOSED_RESTORED'
    a.release(completion, source); assert a.state == 'RELEASED' and a.client.closed == 1
    assert not e.fs.locked
    terminal = dict(kind='named-native-operation-terminal-v1', nonce=NONCE,
       config_sha256=parent_request.sha256, supervisor_pid=5001, supervisor_birth='9001',
       current_resource_state='RELEASED', source_state='CLOSED_RESTORED',
       container_absent=True, container=owner.container, create_issued=True,
       create_completed=True, functional_pass=True, development_lock_identity=identity)
    e.fs.add(ROOT + '/NATIVE-OPERATION-TERMINAL-' + NONCE + '.json', canonical(terminal), mode=0o600)
    evidence = owner.parent.with_name(owner.parent.name + '.owner-' + NONCE[:32])
    e.fs.add(str(evidence), b'', directory=True, mode=0o700)
    data = {'owner.json': dict(nonce=NONCE[:32], outer=dict(pid=5001, proc_starttime=9001),
                             owner_sha256=e.cfg['owner']['sha256']),
       'result.json': dict(container=owner.container, absence_verified=True,
                          lease_retained=False, status='PROTOCOL_PASS'),
       'state.json': dict(Status='exited', ExitCode=0, OOMKilled=False)}
    direct = dict(pid=5101, pgid=5101, sid=5101, proc_starttime=9002, reaped=True, returncode=0)
    initial = dict(pid=5102, pgid=5102, sid=5102, proc_starttime=9003, reaped=False, returncode=None)
    final = dict(initial, reaped=True, returncode=0)
    data.update({'1-inspect.json': dict(command=direct), '2-wait.json': dict(command=initial),
                 'command-retirements-1.json': [dict(initial=initial, final=final)]})
    for name, value in data.items(): e.fs.add(str(evidence) + '/' + name, canonical(value), mode=0o600)
    e.owner_module.LOCK = '/test-only/development.lock'
    w = e.watch.Watchdog.__new__(e.watch.Watchdog)
    w.root_fd=e.root_fd; w.native_request=parent_request; w.nonce=NONCE
    w.pid=5001; w.birth='9001'; w.wait_status=0; w.state='HELD'; w.deadline=CAP; w.grace=2
    w.latch=e.modules['ownership_latch'].CustodyLatch('SUPERVISOR_BOUND')
    e.fs.add('/test-only/current-lease', b''); e.fs.add('/test-only/current-pidfd', b'')
    w.lease_fd=e.fs.open('/test-only/current-lease',os.O_RDONLY)
    w.pidfd=e.fs.open('/test-only/current-pidfd',os.O_RDONLY)
    w.child_record=types.SimpleNamespace(handles=[w.lease_fd,w.pidfd,e.root_fd])
    w.source_loader_holds=[]
    return w, terminal, evidence


def revocation_retirement():
    e = Environment(); a, source, owner = e.held_source()
    # Actual bound-owner cleanup permits only the finite actual-owned verbs.
    a.client.revoked = True; owner.cleaning = True
    reject(lambda: owner._call(['create']), 'revocation permits only actual owned bounded retirement commands')
    owner._call(['inspect', owner.container])
    owner.cleaning = False
    reject(lambda: owner._call(['start', owner.container]), 'test-only current controller veto')
    a.client.revoked = False
    # Execute actual bounded_command orchestration with a virtual direct child.
    m=e.owner_module; born=[]; retired=[]
    class Stream:
        def __init__(self, fd): self.fd=fd; self.closed=False
        def fileno(self): return self.fd
        def close(self):
            e.fs.close(self.fd); self.closed=True
    class LowerChild:
        def __init__(self):
            self.pid=None; self.reaped=False; self.returncode=None; self.stdout=None; self.stderr=None
            self.initial_observation=None
        def acquire(self, argv, env, mask):
            born.append(list(argv)); self.pid=5201
            e.fs.add('/test-only/stdout',b'');e.fs.add('/test-only/stderr',b'')
            self.stdout=Stream(e.fs.open('/test-only/stdout',os.O_RDONLY))
            self.stderr=Stream(e.fs.open('/test-only/stderr',os.O_RDONLY))
        def record(self): return dict(pid=self.pid,pgid=self.pid,sid=self.pid,
             proc_starttime=9004 if self.pid else None,reaped=self.reaped,returncode=self.returncode)
        def retire(self, timeout=1): self.reaped=True;self.returncode=-15;retired.append(self.pid)
        def wait(self, timeout): self.reaped=True;self.returncode=0;return 0
    class LowerSelector:
        def __init__(self): self.rows={}
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def register(self, stream, events, index): self.rows[stream.fd]=types.SimpleNamespace(fd=stream.fd,fileobj=stream,data=index)
        def get_map(self): return self.rows
        def select(self, timeout): return [(key,1) for key in list(self.rows.values())]
        def unregister(self, stream): del self.rows[stream.fd]
    m.CommandChild=LowerChild
    m.selectors=types.SimpleNamespace(DefaultSelector=LowerSelector,EVENT_READ=1)
    ledger=m.CommandLedger()
    def veto(): raise RuntimeError('test-only revoked while lower command is pending')
    reject(lambda: m.bounded_command(['test-only-lower-command'],2,ledger=ledger,admission_check=veto), 'RuntimeError')
    assert len(born)==1 and retired==[5201] and not ledger.pending
    # New state for positive source/native/current-only retirement.
    e=Environment(); a,source,owner=e.held_source()
    historical=e.fs.open('/test-only/scope.json',os.O_RDONLY)
    w,terminal,evidence=prepare_parent_records(e,a,source,owner)
    parent=e.native.NativeParentRetirement(w)
    assert parent.state=='CURRENT_NATIVE_AND_SOURCE_RESTORED' and parent.command_count==2
    # A mismatched late birth cannot become an actual direct wait.
    late=str(evidence)+'/command-retirements-1.json'; saved=bytes(e.fs.files[late]['raw'])
    value=json.loads(saved);value[0]['final']['proc_starttime']+=1;e.fs.add(late,canonical(value))
    reject(lambda:e.native.NativeParentRetirement(w),'actual late direct wait differs')
    e.fs.add(late,saved)
    p=next(iter(source.plan));e.fs.files[p]['flags']^=0x10
    reject(lambda:e.native.NativeParentRetirement(w),'actual source prior inode/flags not restored')
    e.fs.files[p]['flags']^=0x10
    e.fs.locked=True
    reject(lambda:e.native.NativeParentRetirement(w),'development FLOCK still held')
    e.fs.locked=False
    w._poll=lambda until:True;e.fs.wait_result=(w.pid,0)
    result=w.supervise()
    assert result['application_acceptance'] is False and result['actual_client_waits']==2
    assert e.fs.waits==[(w.pid,0)]
    result=w.retire()
    assert result['status']=='RETIRED_CURRENT_NATIVE_OPERATION_ONLY'
    assert result['native_pool']=='STATIC_HELD_UNCHANGED' and result['historical_outcomes']=='UNCHANGED'
    assert historical in e.fs.handles and e.root_fd in e.fs.handles
    # A failed numeric close is recorded once and never retried as retirement.
    e2=Environment();a2,s2,o2=e2.held_source();w2,_,_=prepare_parent_records(e2,a2,s2,o2)
    w2.native_terminal=e2.native.NativeParentRetirement(w2)
    w2.state='CURRENT_NATIVE_RESTORED_PENDING_OWN_FD_CLOSE';e2.fs.close_fail.add(w2.pidfd)
    reject(w2.retire,'current watchdog descriptor close uncertain')
    assert w2.state=='OWN_CLOSURE_UNKNOWN' and e2.fs.closed.count(w2.pidfd)==1
    reject(w2.retire,'positive current native/source/parent retirement required')
    assert e2.fs.closed.count(w2.pidfd)==1
    return dict(precommand_veto=True, during_command_veto=True, actual_owned_cleanup_only=True,
                source_original_flags_restored=True, actual_direct_waits_required=True,
                late_wait_identity_required=True, uncertain_close_not_retried=True,
                retired_scope='CURRENT_NATIVE_OPERATION_ONLY', historical_outcomes='UNCHANGED',
                application_acceptance=False)


FAMILIES={'registered-context':registered_context,'capacity-claim':capacity_claim,
          'effective-source':effective_source,'revocation-retirement':revocation_retirement}
if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in FAMILIES,'one exact family required'
    family=sys.argv[1]
    # SUT modifies sys.argv only inside the registered-loader check.
    result=FAMILIES[family]()
    print(canonical(dict(status='PASS',family=family,result=result,
          real_external_effects=0,native_admission=False,source_permission=False,
          controller1961_rerun=False)).decode())
