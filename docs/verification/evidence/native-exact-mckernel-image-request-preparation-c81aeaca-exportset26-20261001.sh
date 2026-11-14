#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
# Data-only supervisor. This packet never calls ImageOwner.run or takes its lease.
exec /usr/bin/python3 -I -B - "$@" <<'PY'
import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
import traceback
import types

C = 'c81aeaca5cedd893981a058444fa11a03a49a744'
I = '3114d9e7101ad52030eb3effa849a5c108972a1f'
IMAGE = 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'
LOCK = 'fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802'
NIGHTLY = 'rustc 1.95.0-nightly (c04308580 2026-02-18)'
S = '/home/holden/mckernel-work/scratch/'
P = '/home/holden/mckernel/scripts/'
TAG = 'c81aeaca-exportset-26'
cfg = dict(base=S+'native-exact-inputs-c81aeaca-scratch-14.json',
           base_sha='1bf7aea3f3dbccc92a08f307e2b96626a4a24b879bdb592478851e3d2121eed3',
           source=S+'mckernel-exact-candidate-c81aeaca-scratch-14',
           backup=S+'native-exact-metadata-backup-c81aeaca-scratch-14',
           build=S+'native-exact-build-output-4e99a82c-scratch-12',
           nightly=S+'native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu',
           receipt='/home/holden/mckernel-exact-image-evidence-c81aeaca-7/image-receipt.json',
           receipt_sha='824e22c0aad7494914d39adb31bb70290c59912d5326618d2ffeb5cdbb6ef845',
           gitlink=S+'native-exact-mckernel-gitlink-libdwarf-'+TAG,
           gitlink_manifest=S+'native-exact-mckernel-gitlink-inputs-'+TAG+'.json',
           gitlink_manifest_sha='ec6c0995f128153e8b98fca922bc32f78c1aaa2cdd2cebea6cbae57b819cc492',
           helper=P+'native_rust_exact_mckernel_image_request_prepare.py',
           helper_sha='ec3f70b1325a4f91ef1f60dbfba8dd7898440bb6384357fb03c599fa45b41e75',
           owner=P+'native_rust_exact_mckernel_image_container_owner.py',
           owner_sha='1e1e05b2cf07f599c8c6157c4e6921d25a668a5be0ae5bd6bd36b195c3694a1b',
           driver=P+'native_rust_exact_mckernel_image_offline.py',
           driver_sha='91aa047f61167dd93002a0bc12e55b18f4b2fcaf65e246e574e8350a0c37f4cc',
           provenance=P+'native_rust_exact_build_offline.py',
           provenance_sha='cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a',
           host_owner=P+'native_rust_exact_build_container_owner.py',
           host_owner_sha='a8c4c9fc61fab312e3a6e48e93b417453ec12e6543d6adbb7038933f92e79155',
           git='/usr/bin/git', git_sha='c3edb15c9715b79fcfb1fa978256cdfc14a9ad72a4a8d5680a9fc5ebc6a57e0e',
           work=S+'native-exact-mckernel-image-work-'+TAG,
           evidence=S+'native-exact-mckernel-image-owner-evidence-'+TAG,
           inputs=S+'native-exact-mckernel-image-prepare-inputs-'+TAG+'.json',
           toolchain=S+'native-exact-mckernel-image-toolchain-'+TAG+'.json',
           request=S+'native-exact-mckernel-image-request-'+TAG+'.json',
           lease=S+'native-exact-mckernel-image-lease-'+TAG+'.json',
           exclusion=S+'native-exact-candidate-operational-exclusion-exportset-26.json',
           claim=S+'native-exact-mckernel-image-preparation-'+TAG+'.claim',
           log=S+'native-exact-mckernel-image-preparation-'+TAG+'.log',
           terminal=S+'native-exact-mckernel-image-preparation-'+TAG+'-terminal.json',
           host_root='/home/holden', scratch_root=S.rstrip('/'),
           host_device=66306, scratch_device=1831)
PATH_KEYS = tuple(k for k in cfg if not k.endswith(('_sha', '_device')))
AUTH_KEYS = ('base', 'receipt', 'gitlink_manifest', 'helper', 'owner', 'driver', 'provenance', 'host_owner', 'git')
TARGET_KEYS = ('work', 'evidence', 'inputs', 'toolchain', 'request', 'lease', 'exclusion', 'claim', 'log', 'terminal')
SIGNALS = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM}
received = []
for sig in SIGNALS:
    signal.signal(sig, lambda signum, frame: received.append(signum))
test = None

def require(ok, why):
    if not ok:
        raise RuntimeError(why)

def safe(path, kind=None):
    p = Path(path)
    require(p.is_absolute() and '..' not in p.parts, 'noncanonical path: '+str(p))
    require(not any(q.is_symlink() for q in (p, *p.parents)), 'symlink path: '+str(p))
    if kind:
        st = p.stat()
        require(stat.S_ISREG(st.st_mode) if kind == 'file' else stat.S_ISDIR(st.st_mode), 'path type: '+str(p))
    return p

if os.geteuid() == 0:
    sys.exit('root-launch-prohibited')
if sys.argv[1:] or 'MCK_IMAGE26_TEST_CONFIG' in os.environ:
    if sys.argv[1:] != ['--disposable-test'] or not os.environ.get('MCK_IMAGE26_TEST_CONFIG'):
        sys.exit('test-mode-requires-explicit-argument-and-config')
    config_path = safe(os.environ['MCK_IMAGE26_TEST_CONFIG'], 'file')
    test_root = safe(config_path.parent, 'dir')
    require(test_root.parent == Path('/tmp') and test_root.name.startswith('mckernel-image26-test-') and
            test_root.stat().st_uid == os.getuid() and stat.S_IMODE(test_root.stat().st_mode) == 0o700,
            'unsafe-disposable-test-root')
    test = json.loads(config_path.read_text())
    require(not set(test) - (set(cfg) | {'pause_at', 'fail_fsync', 'short_write', 'fail_write', 'deadline'}), 'unknown-test-setting')
    # Every path must be explicitly replaced and confined. Test mode cannot
    # inherit even one production target, dependency or measurement root.
    require(set(PATH_KEYS) <= set(test), 'incomplete-disposable-paths')
    cfg.update({k: v for k, v in test.items() if k in cfg})
    for k in PATH_KEYS:
        p = safe(cfg[k])
        require(test_root in p.parents, 'test-path-outside-disposable-root: '+k)
    cfg['host_device'] = cfg['scratch_device'] = test_root.stat().st_dev

def sha(path):
    h = hashlib.sha256()
    with safe(path, 'file').open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def document(path):
    def pairs(rows):
        out = {}
        for k, v in rows:
            require(k not in out, 'duplicate JSON key: '+k)
            out[k] = v
        return out
    return json.loads(safe(path, 'file').read_text(), object_pairs_hook=pairs)

def same_document(actual, expected):
    # Python equality conflates false/0 and true/1. JSON types are bindings too.
    return json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)

def authenticate():
    for k in AUTH_KEYS:
        require(len(cfg[k+'_sha']) == 64 and sha(cfg[k]) == cfg[k+'_sha'], 'authentication: '+k)

def identity(pid):
    fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, starttime=fields[19], parent=int(fields[1]),
                process_group=int(fields[2]), session=int(fields[3]))

def pidfd_open(pid):
    # The pinned host's Python 3.8 predates os.pidfd_open. Linux x86_64
    # syscall numbers are stable; the kernel, not Python, owns this capability.
    require(os.uname().machine == 'x86_64', 'pidfd syscall architecture')
    fd = ctypes.CDLL(None, use_errno=True).syscall(434, pid, 0)
    if fd < 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return fd

def pidfd_signal(fd, sig):
    result = ctypes.CDLL(None, use_errno=True).syscall(424, fd, sig, 0, 0)
    if result < 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))

def sync(fd, label):
    if test and test.get('fail_fsync') == label:
        raise OSError('injected fsync failure: '+label)
    os.fsync(fd)

def sync_dir(path, label):
    fd = os.open(str(safe(path, 'dir')), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        sync(fd, label)
    finally:
        os.close(fd)

def write_all(fd, data, label='write'):
    while data:
        if test and test.get('fail_write') == label:
            raise OSError('injected write failure: '+label)
        chunk = data[:7] if test and test.get('short_write') else data
        n = os.write(fd, chunk)
        require(n > 0, 'zero-byte write: '+label)
        data = data[n:]

def new_json(path, value, label):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        write_all(fd, (json.dumps(value, sort_keys=True)+'\n').encode(), label)
        sync(fd, label)
    finally:
        os.close(fd)
    sync_dir(Path(path).parent, label+'-parent')

def pause(stage):
    if test and test.get('pause_at') == stage:
        (test_root/('paused-'+stage)).touch()
        end = time.monotonic()+15
        while not (test_root/('resume-'+stage)).exists():
            require(time.monotonic() < end, 'test pause expired')
            time.sleep(.01)

def load_module(key):
    # Compile the exact authenticated bytes, not an import-cache/pyc entry.
    data = safe(cfg[key], 'file').read_bytes()
    require(hashlib.sha256(data).hexdigest() == cfg[key+'_sha'], 'module changed: '+key)
    name = Path(cfg[key]).stem
    module = types.ModuleType(name)
    module.__file__ = cfg[key]
    sys.modules[name] = module
    exec(compile(data, cfg[key], 'exec'), module.__dict__)
    return module

# The fresh interpreter starts with isolated stdlib paths. Its local importer
# compiles only authenticated source bytes carried over stdin: -B alone would
# still permit a timestamp-valid, attacker-supplied __pycache__ entry.
SOURCE_BOOTSTRAP = r'''
import hashlib, importlib, importlib.machinery, importlib.util, json, pathlib, sys
bundle = json.load(sys.stdin)
trusted_path = tuple(sys.path)
local = {}
local_roots = set()
for row in bundle['sources']:
    data = bytes.fromhex(row['source_hex'])
    if hashlib.sha256(data).hexdigest() != row['sha256']:
        raise RuntimeError('bootstrap source authentication: '+row['name'])
    if row['name'] in local or row['name'] in sys.modules:
        raise RuntimeError('bootstrap module collision: '+row['name'])
    local[row['name']] = (row['path'], data)
    local_roots.add(pathlib.Path(row['path']).parent)
class SourceClosure:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in local:
            return importlib.util.spec_from_loader(fullname, self, origin=local[fullname][0])
        # A helper's sys.path.insert must not enable unauthenticated neighboring
        # Python source/bytecode, even when it shadows a standard-library name.
        search = trusted_path if path is None else [p for p in path if not any(
            pathlib.Path(p) == root or root in pathlib.Path(p).parents for root in local_roots)]
        return importlib.machinery.PathFinder.find_spec(fullname, search)
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        path, data = local[module.__name__]
        module.__file__ = path
        exec(compile(data, path, 'exec'), module.__dict__)
sys.meta_path = [importlib.machinery.BuiltinImporter,
                 importlib.machinery.FrozenImporter, SourceClosure()]
for name in bundle['dependencies']:
    importlib.import_module(name)
path, data = local[bundle['helper']]
sys.argv = [path] + bundle['arguments']
exec(compile(data, path, 'exec'), dict(__name__='__main__', __file__=path,
                                     __package__=None, __cached__=None))
'''

def preparer_bundle():
    rows = []
    for key in ('provenance', 'host_owner', 'owner', 'driver', 'helper'):
        data = safe(cfg[key], 'file').read_bytes()
        require(hashlib.sha256(data).hexdigest() == cfg[key+'_sha'], 'bootstrap source changed: '+key)
        rows.append(dict(name=Path(cfg[key]).stem, path=cfg[key], sha256=cfg[key+'_sha'], source_hex=data.hex()))
    return (json.dumps(dict(sources=rows, dependencies=[row['name'] for row in rows[:-1]],
                            helper=rows[-1]['name'], arguments=[cfg['inputs'], '--request', cfg['request']]))+'\n').encode()

def preflight():
    authenticate()  # No claim, mkdir, import or execution precedes this.
    for k in ('source', 'backup', 'build', 'nightly', 'gitlink', 'host_root', 'scratch_root'):
        safe(cfg[k], 'dir')
    for k in TARGET_KEYS:
        safe(cfg[k])
        safe(Path(cfg[k]).parent, 'dir')
        require(not os.path.lexists(cfg[k]), 'target-not-fresh: '+k)
    require(not os.path.lexists(cfg['terminal']+'.pending'), 'terminal staging collision')
    # Targets may neither overlap each other nor any consumed input tree/file.
    targets = [Path(cfg[k]) for k in TARGET_KEYS]
    inputs = [Path(cfg[k]) for k in ('source', 'backup', 'build', 'nightly', 'gitlink', *AUTH_KEYS)]
    for n, p in enumerate(targets):
        for q in targets[n+1:]+inputs:
            require(p != q and p not in q.parents and q not in p.parents, 'overlapping paths')
    for k, floor in (('host', 16*2**30), ('scratch', 12*2**30)):
        p = cfg[k+'_root']
        v = os.statvfs(p)
        require(os.stat(p).st_dev == cfg[k+'_device'], 'device admission: '+k)
        # Disposable fixtures test this branch against their actual filesystem;
        # only their floor is zero. Production floors are literal constants.
        require(v.f_bavail*v.f_frsize >= (0 if test else floor), 'capacity admission: '+k)
    base = document(cfg['base'])
    require(base['candidate_sha'] == C and base['ihk_sha'] == I and
            base['schema'] in ('mckernel.native-exact-build-inputs.v1', 'mckernel.native-exact-mckernel-image-inputs.v1'),
            'candidate identities')
    receipt = document(cfg['receipt'])
    require(receipt['image_id'] == IMAGE and receipt['candidate_sha'] == C and
            receipt['toolchain_lock_sha256'] == LOCK and receipt['status'] == 'PASS' and
            receipt['source_free'] is True and receipt['retired'] is True and
            receipt['runtime_network'] == 'none', 'receipt identities')
    for name, row in receipt['evidence'].items():
        relative = Path(name) if isinstance(name, str) else Path('.')
        require(isinstance(name, str) and name and not relative.is_absolute() and
                name == relative.as_posix() and relative != Path('.') and
                all(part not in ('', '.', '..') for part in relative.parts),
                'receipt evidence name')
        path = safe(Path(cfg['receipt']).parent/relative, 'file')
        require(path.stat().st_size == row['size'] and sha(path) == row['sha256'], 'receipt evidence changed: '+name)
    link = document(cfg['gitlink_manifest'])
    require(link['schema'] == 'mckernel.native-exact-mckernel-gitlink-inputs.v1' and
            link['candidate_sha'] == C and link['ihk_sha'] == I and
            link['base_manifest_sha256'] == cfg['base_sha'], 'gitlink identities')

def expected_documents(owner, driver):
    out, nightly = Path(cfg['build']), Path(cfg['nightly'])
    roots = [dict(path='/out', inventory=owner._closure_inventory(out, out, Path('/out'))),
             dict(path='/nightly', inventory=owner._closure_inventory(nightly, nightly, Path('/nightly')))]
    receipt = document(cfg['receipt'])
    tc = dict(schema='mckernel.native-exact-mckernel-image-toolchain.v2',
              kernel_binding=dict(container_root='/out', container_kernel_dir='/out/build', closure_inventory=roots[0]['inventory']),
              kernel_inventory=driver._tree_inventory(out/'build', visible_roots={'/out': out, '/nightly': nightly}, allow_visible_root=True),
              image_tools={k: receipt['tools'][k] for k in owner.REQUIRED_TOOLS if k != 'rustc'},
              libraries=receipt['libraries'],
              mounted_tools={'rustc': dict(path='/nightly/bin/rustc', sha256=sha(nightly/'bin/rustc'), version=NIGHTLY)},
              toolchain_roots=roots, path_dirs=['/nightly/bin', '/usr/bin'],
              linux_probe=dict(arch='x86_64', release='6.12.0-211.44.1.el10_2.mckernel1.x86_64', kernel_dir='/out/build'), environment={})
    disk = dict(host_root=cfg['host_root'], scratch_root=cfg['scratch_root'],
                host_device=cfg['host_device'], scratch_device=cfg['scratch_device'],
                host_free_floor=16*2**30, scratch_free_floor=12*2**30)
    backup_inventory = owner._tree_inventory(Path(cfg['backup']))
    values = dict(candidate_manifest=cfg['base'], backup_root=cfg['backup'], backup_inventory=backup_inventory,
                  build_output=cfg['build'], image_receipt=cfg['receipt'], image_id=IMAGE,
                  nightly_root=cfg['nightly'], host_git=dict(path=cfg['git'], sha256=cfg['git_sha']),
                  driver_path=cfg['driver'], provenance_path=cfg['provenance'], host_owner_path=cfg['host_owner'],
                  source_root=cfg['source'], owner_work_root=cfg['work'], owner_evidence_root=cfg['evidence'],
                  output_root=str(Path(cfg['work'])/'output'), evidence_root=str(Path(cfg['work'])/'evidence'),
                  attempt_root=str(Path(cfg['evidence'])/'attempt'), lease_path=cfg['lease'],
                  common_exclusion_path=cfg['exclusion'], toolchain_manifest=cfg['toolchain'], jobs=4, timeout=19800,
                  disk_admission=disk, expected_toolchain_lock_sha256=LOCK,
                  gitlink_manifest=cfg['gitlink_manifest'], gitlink_root=cfg['gitlink'])
    req = dict(schema='mckernel.native-exact-mckernel-image-container-request.v1', candidate_sha=C, ihk_sha=I, image_id=IMAGE,
               jobs=4, timeout=19800, source_root=cfg['source'], source_identity=owner._identity(Path(cfg['source'])),
               backup_root=cfg['backup'], backup_identity=owner._identity(Path(cfg['backup'])), backup_inventory=backup_inventory,
               disk_identity=owner._identity(Path(cfg['source'])), source_manifest=cfg['base'], source_manifest_sha256=cfg['base_sha'],
               driver_path=cfg['driver'], driver_sha256=cfg['driver_sha'], provenance_path=cfg['provenance'],
               provenance_sha256=cfg['provenance_sha'], host_owner_path=cfg['host_owner'], host_owner_sha256=cfg['host_owner_sha'],
               toolchain_roots=[dict(host_path=cfg[k], container_path=r['path'], inventory=r['inventory']) for k, r in zip(('build','nightly'), roots)],
               path_dirs=['/nightly/bin', '/usr/bin'], nightly=dict(rustc_version=NIGHTLY), host_git=values['host_git'],
               image_receipt=cfg['receipt'], image_receipt_sha256=cfg['receipt_sha'], toolchain_lock_sha256=LOCK,
               mounts=dict(source='/src', manifest='/inputs.json', toolchain='/toolchain.json', driver='/driver.py',
                           provenance='/native_rust_exact_build_offline.py', work='/work',
                           gitlink_manifest='/libdwarf-inputs.json', gitlink='/src/executer/user/lib/libdwarf/libdwarf'),
               common_exclusion_path=cfg['exclusion'], lease_path=cfg['lease'], owner_evidence_root=cfg['evidence'],
               attempt_root=values['attempt_root'], work_root=cfg['work'], output_root=values['output_root'], evidence_root=values['evidence_root'],
               launcher_aggregate_memory_gib='16.2158', memory_backed_bytes=0, aggregate_memory_required=12*2**30,
               memory_allocation_roots=[cfg['source'], cfg['backup'], cfg['gitlink']], disk_admission=disk,
               gitlink_manifest=cfg['gitlink_manifest'], gitlink_manifest_sha256=cfg['gitlink_manifest_sha'], gitlink_root=cfg['gitlink'],
               toolchain_manifest=cfg['toolchain'])
    return values, tc, req

def publication():
    present = {k: os.path.lexists(cfg[k]) for k in ('toolchain', 'request')}
    state = ('request-published' if present['request'] else 'toolchain-only' if present['toolchain'] else 'no-publication')
    return dict(state=state, present=present)

def worker(resultfd, logfd):
    result = dict(child_returncode=None, semantic_validation='FAIL', hashes={})
    try:
        authenticate()
        load_module('provenance')
        driver = load_module('driver')
        owner = load_module('owner')
        values, initial_tc, initial_req = expected_documents(owner, driver)
        new_json(cfg['inputs'], values, 'inputs')
        authenticate()
        source_bundle = preparer_bundle()
        command = ['/usr/bin/python3', '-I', '-B', '-c', SOURCE_BOOTSTRAP]
        env = dict(PATH='/usr/bin:/bin', HOME='/nonexistent', LANG='C', LC_ALL='C', TZ='UTC',
                   PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', GIT_CONFIG_NOSYSTEM='1',
                   GIT_CONFIG_GLOBAL='/dev/null', GIT_NO_REPLACE_OBJECTS='1', GIT_TERMINAL_PROMPT='0',
                   GIT_OPTIONAL_LOCKS='0', GIT_ALLOW_PROTOCOL='file')
        helper = subprocess.Popen(command, env=env, stdin=subprocess.PIPE)
        write_all(logfd, (json.dumps(dict(command=command, environment=env, helper=identity(helper.pid),
                     helper_argv=[cfg['helper'], cfg['inputs'], '--request', cfg['request']],
                     source_bundle_sha256=hashlib.sha256(source_bundle).hexdigest()))+'\n').encode())
        helper.communicate(source_bundle)
        result['child_returncode'] = helper.returncode
        authenticate()
        # Recompute AFTER child exit; exact whole-document equality also rejects
        # extra keys, reordered mount roots and weakened jobs/timeout settings.
        after_values, tc, req = expected_documents(owner, driver)
        require(same_document(after_values, values) and same_document(document(cfg['inputs']), values), 'input inventory changed')
        require(same_document(tc, initial_tc) and same_document(req, initial_req),
                'initial toolchain/request bindings changed during preparation')
        state = publication()
        if state['present']['toolchain']:
            require(same_document(document(cfg['toolchain']), tc), 'toolchain semantic mismatch')
            result['hashes']['toolchain'] = sha(cfg['toolchain'])
        if state['present']['request']:
            require(state['present']['toolchain'], 'request without toolchain')
            req['toolchain_manifest_sha256'] = result['hashes']['toolchain']
            actual = document(cfg['request'])
            require(same_document(actual, req), 'request semantic mismatch')
            owner.ImageOwner(actual).validate()  # Read-only; never .run().
            result['hashes']['request'] = sha(cfg['request'])
        result['semantic_validation'] = 'PASS'
        result['publication'] = state
    except BaseException as exc:
        result['error'] = repr(exc)
        traceback.print_exc()
    result['publication'] = publication()
    write_all(resultfd, (json.dumps(result)+'\n').encode())
    os._exit(0)

def retire():
    # prctl subreaping makes ordinary orphan descendants ours, including ones
    # which changed session. pidfds plus starttime checks avoid PID-reuse kills.
    for sig, grace in ((signal.SIGTERM, .25), (signal.SIGKILL, 3.0)):
        end = time.monotonic()+grace
        while time.monotonic() < end:
            rows = {}
            for entry in Path('/proc').iterdir():
                if entry.name.isdigit():
                    try:
                        row = identity(int(entry.name))
                        rows[row['pid']] = row
                    except (FileNotFoundError, ProcessLookupError):
                        pass
            ours = {os.getpid()}
            while True:
                more = {pid for pid, row in rows.items() if row['parent'] in ours}
                if more <= ours:
                    break
                ours |= more
            for pid in ours-{os.getpid()}:
                fd = None
                try:
                    fd = pidfd_open(pid)
                    if identity(pid)['starttime'] == rows[pid]['starttime']:
                        pidfd_signal(fd, sig)
                except (ProcessLookupError, FileNotFoundError):
                    pass
                finally:
                    if fd is not None:
                        os.close(fd)
            while True:
                try:
                    pid, status = os.waitpid(-1, os.WNOHANG)
                    if not pid:
                        break
                except ChildProcessError:
                    return True
            time.sleep(.01)
    return False

owner_id = identity(os.getpid())
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
logfd = child = readfd = gatefd = None
claimed = False
retired = True
result = {}
rc = 1
try:
    preflight()
    require(not received, 'signal before claim')
    new_json(cfg['claim'], dict(schema='mckernel.image-preparation-claim.v1', owner=owner_id, boot_id=boot,
                              targets={k: cfg[k] for k in TARGET_KEYS}, inputs={k: cfg[k+'_sha'] for k in AUTH_KEYS}), 'claim')
    claimed = True
    logfd = os.open(cfg['log'], os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    write_all(logfd, (json.dumps(dict(owner=owner_id, boot_id=boot, bindings=cfg))+'\n').encode())
    sync(logfd, 'initial-log')
    sync_dir(Path(cfg['log']).parent, 'initial-log-parent')
    # Recheck targets after acquiring the persistent namespace claim.
    for k in TARGET_KEYS:
        if k not in ('claim', 'log'):
            require(not os.path.lexists(cfg[k]), 'target raced claim: '+k)
    for k in ('work', 'evidence'):
        os.mkdir(cfg[k], 0o700)
        sync_dir(cfg[k], k)
        sync_dir(Path(cfg[k]).parent, k+'-parent')
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(36, 1, 0, 0, 0) == 0, 'subreaper unavailable')
    capability_fd = pidfd_open(os.getpid())
    os.close(capability_fd)
    readfd, writefd = os.pipe()
    gateread, gatefd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(readfd)
        os.close(gatefd)
        os.setsid()
        for sig in SIGNALS:
            signal.signal(sig, signal.SIG_DFL)
        os.dup2(logfd, 1)
        os.dup2(logfd, 2)
        if os.read(gateread, 1) != b'G':
            os._exit(1)
        os.close(gateread)
        worker(writefd, logfd)
    os.close(writefd)
    os.close(gateread)
    child = identity(pid)
    retired = False
    session_deadline = time.monotonic()+2
    while child['session'] != pid:
        require(time.monotonic() < session_deadline and not received, 'child session admission')
        time.sleep(.001)
        child = identity(pid)
    write_all(logfd, (json.dumps(dict(child=child, boot_id=boot))+'\n').encode())
    sync(logfd, 'child-log')
    write_all(gatefd, b'G')
    os.close(gatefd)
    gatefd = None
    deadline = time.monotonic()+(test.get('deadline', 30) if test else 1800)
    status = None
    while not received and time.monotonic() < deadline:
        status = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if status is not None:
            break
        time.sleep(.02)
    rc = 128+received[0] if received else 124 if status is None else 0 if status.si_code == os.CLD_EXITED and status.si_status == 0 else 1
except BaseException as exc:
    rc = 1
    try:
        write_all(logfd if logfd is not None else 2, ('SUPERVISOR_ERROR='+repr(exc)+'\n').encode())
    except OSError:
        pass
finally:
    if gatefd is not None:
        os.close(gatefd)
    if child is not None:
        try:
            retired = retire()
        except BaseException:
            retired = False
        if not retired:
            rc = 1
    if readfd is not None:
        os.set_blocking(readfd, False)
        try:
            raw = os.read(readfd, 65536)
            result = json.loads(raw)
        except (OSError, ValueError):
            if rc == 0:
                rc = 1
        finally:
            os.close(readfd)

if not claimed or logfd is None:
    os._exit(1)
try:
    pause('before-commit')
    # Keep these signals blocked through stdout and _exit. A late signal can
    # neither truncate the terminal nor turn a delivered success into exit 143.
    signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
    pending = signal.sigpending() & SIGNALS
    if received or pending:
        rc = 128+(received[0] if received else min(pending))
    state = publication()
    if rc == 0 and not (result.get('child_returncode') == 0 and result.get('semantic_validation') == 'PASS' and
                        result.get('publication') == state and state['state'] == 'request-published'):
        rc = 1
    observed = {}
    for k, present in state['present'].items():
        if present:
            try:
                observed[k] = sha(cfg[k])
                if rc == 0:
                    require(observed[k] == result['hashes'][k], 'output changed after validator: '+k)
                fd = os.open(cfg[k], os.O_RDONLY | os.O_NOFOLLOW)
                try:
                    sync(fd, k)
                finally:
                    os.close(fd)
                sync_dir(Path(cfg[k]).parent, k+'-parent')
            except BaseException as exc:
                rc = 1
                observed[k] = dict(error=repr(exc))
    require(retired, 'descendant retirement unproven')
    terminal = dict(schema='mckernel.native-exact-image-preparation-terminal.v1', returncode=rc,
                    owner=owner_id, child=child, boot_id=boot, child_retired=retired,
                    publication=state, observed_hashes=observed, validation=result,
                    log=cfg['log'], late_signal_policy='blocked-after-commit-boundary',
                    acceptance_requires='zero-wrapper-exit-and-matching-stdout-commit-witness',
                    stdout_delivery='not-asserted-by-terminal-existence')
    write_all(logfd, (json.dumps(dict(final=terminal))+'\nPREPARATION_RESULT='+('PASS' if rc == 0 else 'FAIL')+'\n').encode(), 'final-log')
    sync(logfd, 'log')
    sync_dir(Path(cfg['log']).parent, 'log-parent')
    log_stat = os.fstat(logfd)
    path_stat = safe(cfg['log'], 'file').stat()
    require((log_stat.st_dev, log_stat.st_ino, log_stat.st_size) ==
            (path_stat.st_dev, path_stat.st_ino, path_stat.st_size), 'log pathname substituted')
    terminal['log_sha256'] = sha(cfg['log'])
    stage = cfg['terminal']+'.pending'
    new_json(stage, terminal, 'terminal')
    os.link(stage, cfg['terminal'], follow_symlinks=False)
    sync_dir(Path(cfg['terminal']).parent, 'terminal-publication')
    pause('after-terminal')
    witness = dict(terminal=cfg['terminal'], terminal_sha256=sha(cfg['terminal']), log=cfg['log'],
                   log_sha256=terminal['log_sha256'], preparation_returncode=rc, publication=state['state'])
    write_all(1, (json.dumps(witness, sort_keys=True)+'\n').encode(), 'stdout')
    os.close(logfd)
    os._exit(rc)
except BaseException as exc:
    try:
        write_all(2, ('publication-or-delivery-failed: '+repr(exc)+'\n').encode())
    finally:
        os._exit(1)
PY
