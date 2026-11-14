#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
# exec preserves the shell PID/starttime; one supervisor owns the whole protocol.
exec /usr/bin/python3 -I -B - "$@" <<'PY'
import ctypes
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import stat
import subprocess
import sys
import time
import traceback

CANDIDATE = '6fed3a1022db0b4f9828dd42a8bd8f88fc052053'
IHK = '3114d9e7101ad52030eb3effa849a5c108972a1f'
SCRATCH = '/home/holden/mckernel-work/scratch/'
cfg = dict(base=SCRATCH+'native-exact-inputs-6fed3a10-scratch-13.json',
           base_sha='fbfde0a1d83501c8411a8163dd8acb37952c5e110339d166fe83c9c2fdec3161',
           helper='/home/holden/mckernel/scripts/native_rust_exact_mckernel_gitlink_prepare.py',
           helper_sha='d1cee2c5ab37c2d86328b6a5999f5a7f15cea38ba80c0948ae749aab79f6a597',
           src=SCRATCH+'native-exact-mckernel-gitlink-libdwarf-4e99a82c-exportset-23',
           dest=SCRATCH+'native-exact-mckernel-gitlink-libdwarf-6fed3a10-exportset-25',
           out=SCRATCH+'native-exact-mckernel-gitlink-inputs-6fed3a10-exportset-25.json',
           log=SCRATCH+'native-exact-mckernel-gitlink-preparation-6fed3a10-exportset-25.log',
           terminal=SCRATCH+'native-exact-mckernel-gitlink-preparation-6fed3a10-exportset-25-terminal.json')
signals = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM}
received = []
for sig in signals:
    signal.signal(sig, lambda signum, frame: received.append(signum))
test = None
if os.geteuid() == 0:
    sys.exit('root-launch-prohibited')
if sys.argv[1:] or 'MCK_GITLINK25_TEST_CONFIG' in os.environ:
    if sys.argv[1:] != ['--disposable-test'] or not os.environ.get('MCK_GITLINK25_TEST_CONFIG'):
        sys.exit('test-mode-requires-explicit-argument-and-config')
    config_path = Path(os.environ['MCK_GITLINK25_TEST_CONFIG'])
    root = config_path.parent
    if (not root.is_absolute() or root.parent != Path('/tmp') or
            not root.name.startswith('mckernel-gitlink25-test-') or root.is_symlink() or
            root.stat().st_uid != os.getuid() or stat.S_IMODE(root.stat().st_mode) != 0o700):
        sys.exit('unsafe-disposable-test-root')
    test = json.loads(config_path.read_text())
    if set(test) - (set(cfg) | {'pause_at', 'fail_fsync'}):
        sys.exit('unknown-test-setting')
    cfg.update({k: v for k, v in test.items() if k in cfg})
    for k in ('base', 'helper', 'src', 'dest', 'out', 'log', 'terminal'):
        p = Path(cfg[k])
        if p.parent != root or p.is_symlink():
            sys.exit('test-path-outside-disposable-root')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(ok, why):
    if not ok:
        raise RuntimeError(why)

def identity(pid):
    text = Path('/proc/%d/stat' % pid).read_text()
    return {'pid': pid, 'starttime': text[text.rfind(')')+2:].split()[19]}

def sync(fd, label):
    if test and test.get('fail_fsync') == label:
        raise OSError('injected fsync failure: '+label)
    os.fsync(fd)

def sync_parent(path, label):
    fd = os.open(str(Path(path).parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        sync(fd, label)
    finally:
        os.close(fd)

def write_all(fd, data):
    while data:
        n = os.write(fd, data)
        require(n > 0, 'zero-byte write')
        data = data[n:]

def pause(stage):
    if test and test.get('pause_at') == stage:
        (root / ('paused-'+stage)).touch()
        deadline = time.monotonic()+10
        while not (root / ('resume-'+stage)).exists():
            require(time.monotonic() < deadline, 'test pause expired')
            time.sleep(.01)

def validate():
    # Inventory and all its git subprocesses stay in the controlled session.
    helper = runpy.run_path(cfg['helper'], run_name='packet_inventory')
    require(sha(cfg['helper']) == cfg['helper_sha'], 'helper changed')
    require(sha(cfg['base']) == cfg['base_sha'], 'base changed')
    data = json.loads(Path(cfg['out']).read_text())
    base = json.loads(Path(cfg['base']).read_text())
    path = 'executer/user/lib/libdwarf/libdwarf'
    require(base['candidate_sha'] == CANDIDATE and base['ihk_sha'] == IHK, 'base identities')
    require(data['schema'] == 'mckernel.native-exact-mckernel-gitlink-inputs.v1', 'schema')
    require(data['candidate_sha'] == CANDIDATE and data['ihk_sha'] == IHK, 'identities')
    require(data['base_manifest_sha256'] == cfg['base_sha'], 'base digest')
    require(set(data['consumed_gitlinks']) == {path}, 'consumed gitlink set')
    actual = helper['inventory'](Path(cfg['dest']))
    expected = dict(path=path, commit=actual['head'], tree=actual['tree'],
                    files=actual['files'], git_metadata=actual['git_metadata'])
    require(data['consumed_gitlinks'][path] == expected, 'checkout inventory differs')
    require(actual['head'] == base['gitlinks'][path], 'checkout commit differs')
    require(data['preparer_git'] == helper['_authenticate_git'](), 'git tool identity')
    return sha(cfg['out'])

owner = identity(os.getpid())
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
child = None
logfd = None
claimed = False
retired = True
rc = 1
output_sha = None
resultfd = None
gatefd = None
try:
    require(Path(cfg['src']).is_dir() and not Path(cfg['src']).is_symlink(), 'source absent')
    require(sha(cfg['base']) == cfg['base_sha'], 'base digest mismatch')
    require(sha(cfg['helper']) == cfg['helper_sha'], 'helper digest mismatch')
    # Retained exclusive claims cover all helper-owned names too. No existing
    # file is opened for truncation, including when another packet races us.
    for key in ('dest', 'out', 'log', 'terminal'):
        path = cfg[key]
        fd = os.open(path+'.claim', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            write_all(fd, (json.dumps(dict(owner=owner, boot_id=boot))+'\n').encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        sync_parent(path, 'claim-parent')
        require(not os.path.lexists(path), 'target-exists: '+path)
    claimed = True
    logfd = os.open(cfg['log'], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    write_all(logfd, (json.dumps(dict(owner=owner, boot_id=boot, inputs=cfg))+'\n').encode())
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(36, 1, 0, 0, 0) == 0, 'subreaper unavailable')
    resultfd, resultwrite = os.pipe()
    gateread, gatefd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(resultfd)
        os.close(gatefd)
        os.setsid()
        for sig in signals:
            signal.signal(sig, signal.SIG_DFL)
        os.dup2(logfd, 1)
        os.dup2(logfd, 2)
        # Parent records identity before authorizing any helper subprocess.
        if os.read(gateread, 1) != b'G':
            os._exit(1)
        os.close(gateread)
        try:
            env = dict(PATH='/usr/bin:/bin', HOME='/nonexistent', LANG='C', LC_ALL='C', TZ='UTC',
                       PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', GIT_CONFIG_NOSYSTEM='1',
                       GIT_CONFIG_GLOBAL='/dev/null', GIT_NO_REPLACE_OBJECTS='1',
                       GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='file')
            command = ['/usr/bin/python3', '-I', '-B', cfg['helper'],
                       '--source', cfg['src'], '--checkout', cfg['dest'],
                       '--output', cfg['out'], '--base-manifest', cfg['base'],
                       '--candidate-sha', CANDIDATE, '--ihk-sha', IHK]
            helper_process = subprocess.Popen(command, env=env)
            print(json.dumps(dict(helper=identity(helper_process.pid), boot_id=boot,
                                  command=command, environment=env)), flush=True)
            status = helper_process.wait()
            require(status == 0, 'helper exit '+str(status))
            digest = validate()
            write_all(resultwrite, (digest+'\n').encode())
            os._exit(0)
        except BaseException:
            traceback.print_exc()
            sys.stderr.flush()
            os._exit(1)
    os.close(resultwrite)
    os.close(gateread)
    child = identity(pid)
    retired = False
    write_all(logfd, (json.dumps(dict(child=child, boot_id=boot))+'\n').encode())
    write_all(gatefd, b'G')
    os.close(gatefd)
    gatefd = None
    deadline = time.monotonic()+600
    status = None
    while not received and time.monotonic() < deadline:
        status = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if status is not None:
            break
        time.sleep(.02)
    else:
        status = None
    if received:
        rc = 128+received[0]
    elif status is None:
        rc = 124
    else:
        rc = 0 if status.si_code == os.CLD_EXITED and status.si_status == 0 else 1
except BaseException as exc:
    if logfd is not None:
        write_all(logfd, ('SUPERVISOR_ERROR='+repr(exc)+'\n').encode())
    else:
        print(str(exc), file=sys.stderr)
    rc = 1
finally:
    if gatefd is not None:
        os.close(gatefd)
    if child is not None:
        # Trusted helper/git processes inherit this session. Subreaping makes
        # orphaned grandchildren waitable before publishing a terminal outcome.
        for sig, grace in ((signal.SIGTERM, .25), (signal.SIGKILL, 3.0)):
            try:
                os.killpg(child['pid'], sig)
            except ProcessLookupError:
                pass
            end = time.monotonic()+grace
            while time.monotonic() < end:
                try:
                    found, unused = os.waitpid(-1, os.WNOHANG)
                    if not found:
                        time.sleep(.01)
                except ChildProcessError:
                    retired = True
                    break
            if retired:
                break
        if not retired:
            rc = 1
    if resultfd is not None:
        os.set_blocking(resultfd, False)
        try:
            result = os.read(resultfd, 128)
            if rc == 0:
                require(len(result) == 65 and result[-1:] == b'\n', 'missing full validator result')
                output_sha = result[:-1].decode('ascii')
        except BaseException:
            rc = 1
        finally:
            os.close(resultfd)

if not claimed or logfd is None:
    os._exit(1)
try:
    pause('before-commit')
    # Commit boundary: earlier signals fail; later HUP/INT/TERM remain blocked
    # through log/terminal fsync, stdout delivery and _exit (never reset traps).
    signal.pthread_sigmask(signal.SIG_BLOCK, signals)
    pending = signal.sigpending() & signals
    if received or pending:
        rc = 128+(received[0] if received else min(pending))
    require(retired, 'descendant retirement unproven')
    if rc == 0:
        require(output_sha is not None and sha(cfg['out']) == output_sha, 'manifest changed after validation')
        fd = os.open(cfg['out'], os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        sync_parent(cfg['out'], 'output-parent')
    write_all(logfd, ('PREPARATION_RESULT='+('PASS' if rc == 0 else 'FAIL')+'\nTERMINAL_RC='+str(rc)+'\n').encode())
    sync(logfd, 'log')
    sync_parent(cfg['log'], 'log-parent')
    terminal = dict(schema='mckernel.native-exact-gitlink-preparation-terminal.v3',
                    returncode=rc, owner=owner, child=child, boot_id=boot,
                    child_retired=retired, log=cfg['log'], log_sha256=sha(cfg['log']),
                    output_sha256=output_sha, late_signal_policy='blocked-after-commit-boundary',
                    stdout_delivery='not-part-of-durable-preparation-outcome',
                    acceptance_requires='zero-wrapper-exit-and-stdout-commit-witness')
    fd = os.open(cfg['terminal'], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        write_all(fd, (json.dumps(terminal, sort_keys=True)+'\n').encode())
        sync(fd, 'terminal')
    finally:
        os.close(fd)
    sync_parent(cfg['terminal'], 'terminal-parent')
    pause('after-terminal')
    # A file commit and a pipe write cannot be atomic. Delivery failures exit
    # nonzero; the terminal describes preparation, never asserts stdout delivery.
    write_all(1, (json.dumps(dict(terminal=cfg['terminal'], terminal_sha256=sha(cfg['terminal']), preparation_returncode=rc,
                                 log_final_fsync='PASS'))+'\n').encode())
    os.close(logfd)
    os._exit(rc)
except BaseException as exc:
    try:
        write_all(2, ('publication-or-delivery-failed: '+repr(exc)+'\n').encode())
    finally:
        os._exit(1)
PY
