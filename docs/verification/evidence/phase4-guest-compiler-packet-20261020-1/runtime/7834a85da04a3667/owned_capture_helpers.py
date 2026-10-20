from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
stopping=False
STOP_SIGNALS={signal.SIGTERM,signal.SIGINT,signal.SIGALRM}
CENSUS_SOURCE=Path('/accepted-host-owner.py')
CENSUS_SHA='96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1'
_CENSUS=None
def need(ok, message):
    if not ok:
        raise ValueError(message)

def write(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 384)
    with os.fdopen(fd, 'w') as f:
        json.dump(value, f, sort_keys=True)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())

def hashed(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        a = os.fstat(fd)
        need(stat.S_ISREG(a.st_mode) and a.st_nlink == 1 and (a.st_size <= maximum), 'bounded regular singlelink FD')
        h = hashlib.sha256()
        size = 0
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            size += len(block)
            need(size <= maximum, 'capture growth')
            h.update(block)
        b = os.fstat(fd)
        c = path.lstat()
        need(all((getattr(a, k) == getattr(b, k) == getattr(c, k) for k in FIELDS)) and size == b.st_size, 'stable FD metadata')
        return dict(path=str(path), sha256=h.hexdigest(), device=b.st_dev, inode=b.st_ino, uid=b.st_uid, gid=b.st_gid, mode=oct(stat.S_IMODE(b.st_mode)), nlink=b.st_nlink, size=size, mtime_ns=b.st_mtime_ns, ctime_ns=b.st_ctime_ns)
    finally:
        os.close(fd)

def stop(signum, frame):
    global stopping
    if stopping:
        return
    stopping = True
    signal.setitimer(signal.ITIMER_REAL, 0)
    raise InterruptedError('ordinary envelope signal ' + str(signum))

def members(pgid):
    global _CENSUS
    if _CENSUS is None:
        raw = CENSUS_SOURCE.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == CENSUS_SHA, 'pinned accepted census source')
        tree = ast.parse(raw, str(CENSUS_SOURCE))
        cls = next((x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == 'Docker'))
        fn = next((x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == '_surviving_group_members'))
        namespace = {'Path': Path}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(CENSUS_SOURCE), 'exec'), namespace)
        _CENSUS = namespace[fn.name]
    context = type('CensusContext', (), {})()
    context.client_retirement_unproven = False
    found = _CENSUS(context, pgid)
    need(not context.client_retirement_unproven, 'accepted census uncertainty')
    return sorted(found)

def process_start(pid):
    return int(Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()[19])

def terminal_unreaped(process):
    return os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None

def wait_terminal(process, seconds):
    deadline = time.monotonic() + seconds
    while not terminal_unreaped(process):
        if time.monotonic() >= deadline:
            return False
        time.sleep(min(0.01, max(0, deadline - time.monotonic())))
    return True

def owned_capture(command, path, wall_seconds, limits, started_reader=process_start):
    """Fixed ordinary child; errors always retire/join before stream FD reads.

 No signal is sent after reap. Unexpected descendants make this fixed-command
 envelope fail closed even if termination succeeds; their independent reaping
 is not invented. The caller's direct child remains unreaped while signalling.
 """
    global stopping
    process = None
    birth = None
    rc = None
    direct = False
    error = None
    retirement_error = None
    timed = False
    unexpected = []
    begin = time.monotonic()
    outfd = os.open(path / 'stdout', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 384)
    try:
        errfd = os.open(path / 'stderr', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 384)
    except BaseException:
        os.close(outfd)
        raise
    with os.fdopen(outfd, 'wb') as out, os.fdopen(errfd, 'wb') as err:
        try:
            previous = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
            try:

                def child_limits():
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous)
                    limits()
                process = subprocess.Popen(command['argv'], stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True, preexec_fn=child_limits)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous)
            birth = started_reader(process.pid)
            write(path / 'started.json', dict(pid=process.pid, start=birth))
            if not wait_terminal(process, wall_seconds):
                raise subprocess.TimeoutExpired(command['argv'], wall_seconds)
        except BaseException as exc:
            error = type(exc).__name__ + ': ' + str(exc)
            timed = isinstance(exc, subprocess.TimeoutExpired)
        finally:
            if process is not None:
                previous = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
                if error is not None:
                    stopping = True
                    signal.setitimer(signal.ITIMER_REAL, 0)
                anchored = False
                try:
                    terminal_unreaped(process)
                    anchored = True
                    group = members(process.pid)
                    unexpected = [pid for pid in group if pid != process.pid]
                    if unexpected and error is None:
                        error = 'unexpected fixed-command group members'
                    if error is not None:
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        ended = wait_terminal(process, 2)
                        group = members(process.pid)
                        if not ended or any((pid != process.pid for pid in group)):
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            need(wait_terminal(process, 2), 'owned creator did not terminate after KILL')
                except BaseException as exc:
                    retirement_error = type(exc).__name__ + ': ' + str(exc)
                    if anchored:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        except BaseException as kill_error:
                            retirement_error += '; KILL ' + repr(kill_error)
                finally:
                    try:
                        rc = process.wait(timeout=2)
                        direct = True
                        write(path / 'direct-wait.json', dict(pid=process.pid, start=birth, returncode=rc, direct_child_joined=True))
                    except BaseException as exc:
                        retirement_error = (retirement_error or '') + '; direct wait ' + repr(exc)
                    finally:
                        signal.pthread_sigmask(signal.SIG_SETMASK, previous)
        absent = False
        remaining = []
        if process is not None and direct:
            try:
                remaining = members(process.pid)
                absent = not remaining
            except BaseException as exc:
                retirement_error = (retirement_error or '') + '; final census ' + repr(exc)
        joined = dict(pid=process.pid if process else None, start=birth, returncode=rc, direct_child_joined=direct, group_absent=absent, remaining_group_members=remaining, unexpected_group_members=unexpected, timed_out=timed, error=error, retirement_error=retirement_error, seconds=time.monotonic() - begin)
        write(path / 'direct-join.json', joined)
    joined['closed_streams'] = True
    joined['captures'] = {name: hashed(path / name, 32 << 20) for name in ('stdout', 'stderr')}
    return joined
