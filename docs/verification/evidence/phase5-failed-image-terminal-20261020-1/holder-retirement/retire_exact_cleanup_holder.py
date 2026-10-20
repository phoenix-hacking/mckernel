"""Exact current2017001 cleanup-holder retirement only. Root executes after independent release.
No Docker, workload, record deletion or historical recovery execution.
"""
import argparse,ast,ctypes,fcntl,hashlib,json,os,re,select,signal,stat,time
from pathlib import Path
R=Path(__file__).resolve().parent
SELF=Path(__file__).resolve()
PID,START,PARENT=2017001,'29360720',2016998
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
LOCK=Path('/run/lock/mckernel-development.lock')
SMALL_LIMIT=1<<20
FILE_LIMIT=128<<20
DEFERRED_SIGNALS=(signal.SIGHUP,signal.SIGINT,signal.SIGTERM,signal.SIGQUIT)
O=R/'root-effects-1'
QUARANTINE=O/'uncertain-recovery.json'
class Refusal(RuntimeError):pass

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'

def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refusal('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refusal('nonfinite JSON')))

def directory(path):
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('noncanonical path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                          dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise

def file_identity(path, keep=False, maximum=FILE_LIMIT):
    """Stream SHA256; stable metadata excludes atime and never follows an alias."""
    parent = directory(path.parent)
    fd = None
    try:
        # The sole fixed root-owned executable cannot use O_NOATIME as holden.
        # Its reviewed node/hash is stable without atime; no received-file fallback.
        noatime = 0 if path == Path('/usr/bin/python3.8') else os.O_NOATIME
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | noatime | os.O_CLOEXEC |
                     os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum or before.st_nlink != 1:
            raise Refusal('protected regular file shape')
        digest, chunks, count = hashlib.sha256(), [], 0
        while count <= before.st_size:
            raw = os.read(fd, min(1 << 20, before.st_size + 1 - count))
            if not raw:
                break
            digest.update(raw)
            count += len(raw)
            if keep:
                chunks.append(raw)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        after = os.fstat(fd)
        linked = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if (count != before.st_size or any(getattr(before, k) != getattr(after, k) for k in fields) or
                any(getattr(before, k) != getattr(linked, k) for k in fields)):
            raise Refusal('protected file changed')
        row = dict(path=str(path), device=before.st_dev, inode=before.st_ino,
                   size=before.st_size, mode=stat.S_IMODE(before.st_mode),
                   uid=before.st_uid, gid=before.st_gid, nlink=before.st_nlink,
                   sha256=digest.hexdigest())
        return row, b''.join(chunks) if keep else None
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)

def read_json(path, expected=None):
    row, raw = file_identity(path, keep=True, maximum=SMALL_LIMIT)
    if expected is not None and row['sha256'] != expected:
        raise Refusal('JSON digest differs')
    return strict(raw)

def publish(path, raw):
    parent = directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW |
                     os.O_CLOEXEC, 0o600, dir_fd=parent)
        remaining = memoryview(raw)
        while remaining:
            count = os.write(fd, remaining)
            if count <= 0:
                raise Refusal('publication made no progress')
            remaining = remaining[count:]
        os.fsync(fd)
        os.fsync(parent)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)

def proc_bytes(path, maximum=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, maximum + 1 - total))
            if not chunk:
                return b''.join(chunks)
            total += len(chunk)
            if total > maximum:
                raise Refusal('proc observation exceeds bound')
            chunks.append(chunk)
    finally:
        os.close(fd)

def proc_stat(pid):
    raw = proc_bytes('/proc/%d/stat' % pid, 4096).decode()
    prefix, separator, tail = raw.rpartition(') ')
    fields = tail.split()
    if not separator or not prefix.startswith(str(pid) + ' (') or len(fields) < 20:
        raise Refusal('process stat malformed')
    return fields

def boot_check():
    if proc_bytes('/proc/sys/kernel/random/boot_id', 128).decode().strip() != BOOT:
        raise Refusal('current boot differs')

def guard_identity(profile):
    boot_check()
    guard = profile['bound_guard']
    fields = proc_stat(PID)
    if fields[19] != START or int(fields[1]) != PARENT or fields[0] in ('Z', 'X', 'x'):
        raise Refusal('guard start/parent/state differs')
    status = dict(line.split(':', 1) for line in proc_bytes('/proc/%d/status' % PID).decode().splitlines() if ':' in line)
    if (status.get('Uid', '').split() != ['0'] * 4 or status.get('Gid', '').split() != ['0'] * 4 or
            status.get('Threads', '').strip() != '1'):
        raise Refusal('guard credentials or thread count differs')
    if proc_bytes('/proc/%d/cmdline' % PID) != b'\0'.join(arg.encode() for arg in guard['argv']) + b'\0':
        raise Refusal('guard argv differs')
    if os.readlink('/proc/%d/exe' % PID) != guard['exe']:
        raise Refusal('guard executable link differs')
    exe = os.stat('/proc/%d/exe' % PID)
    if (exe.st_dev, exe.st_ino, exe.st_size) != (guard['exe_device'], guard['exe_inode'], guard['exe_size']):
        raise Refusal('guard executable node differs')
    if file_identity(Path(guard['source']))[0]['sha256'] != guard['source_sha256']:
        raise Refusal('guard source differs')
    parent=proc_stat(PARENT)
    if parent[19]!=profile['original_processes'][str(PARENT)]['starttime'] or int(parent[1])!=2016997 or parent[0] in ('Z','X','x'):raise Refusal('original sudo parent identity differs')
    if os.readlink('/proc/%d/exe'%PARENT)!=' /usr/bin/sudo'.strip():raise Refusal('original sudo executable differs')
    expected=profile['saved_child']['fds']
    if set(os.listdir('/proc/%d/fd'%PID))!={str(row['fd']) for row in expected}:raise Refusal('target exact7 FD set differs')
    for row in expected:
        path='/proc/%d/fd/%d'%(PID,row['fd'])
        meta=os.stat(path)
        if os.readlink(path)!=row['target'] or (meta.st_dev,meta.st_ino,meta.st_mode)!=(row['dev'],row['ino'],row['mode']):raise Refusal('target saved FD node differs')
    if proc_bytes('/proc/%d/task/%d/children'%(PID,PID)).strip():raise Refusal('target acquired descendants')
    require_lock_holder(PID);require_transaction_lock_holder(PID)
    if proc_stat(PID)[19] != START:
        raise Refusal('guard raced during identity read')
    return dict(pid=PID, starttime=START, parent=PARENT, boot_id=BOOT, uid=0, gid=0, threads=1)

def lock_rows():
    rows = []
    for line in proc_bytes('/proc/locks', SMALL_LIMIT).decode().splitlines():
        fields = line.split()
        if '->' in fields:
            fields.remove('->')
        if len(fields) != 8:
            raise Refusal('kernel lock report malformed')
        major, minor, inode = fields[5].split(':')
        if (int(major, 16), int(minor, 16), int(inode)) == (0, 27, 4):
            rows.append(fields[1:])
    return rows

def require_lock_holder(pid):
    rows = lock_rows()
    if len(rows) != 1 or rows[0] != ['FLOCK', 'ADVISORY', 'WRITE', str(pid), '00:1b:4', '0', 'EOF']:
        raise Refusal('sole preserved root flock holder differs')
    return rows

def transaction_lock_rows():
    rows = []
    for line in proc_bytes('/proc/locks', SMALL_LIMIT).decode().splitlines():
        fields = line.split()
        if '->' in fields:
            fields.remove('->')
        if len(fields) != 8:
            raise Refusal('kernel lock report malformed')
        major, minor, inode = fields[5].split(':')
        if (int(major, 16), int(minor, 16), int(inode)) == (7, 36, 116137):
            rows.append(fields[1:])
    return rows

def require_transaction_lock_holder(pid):
    rows=transaction_lock_rows()
    if len(rows)!=1 or rows[0]!=['FLOCK','ADVISORY','WRITE',str(pid),'07:24:116137','0','EOF']:raise Refusal('sole exact transaction flock holder differs')
    return rows


def pidfd_open():
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    fd = libc.syscall(434, ctypes.c_int(PID), ctypes.c_uint(0))
    if fd < 0:
        raise OSError(ctypes.get_errno(), 'pidfd_open unavailable; no fallback')
    return int(fd)

def bind_pidfd(fd, profile):
    fields = dict(line.split(':', 1) for line in proc_bytes('/proc/self/fdinfo/%d' % fd, 4096).decode().splitlines() if ':' in line)
    if fields.get('Pid', '').strip() != str(PID):
        raise Refusal('pidfd target identity differs')
    return guard_identity(profile)

def sole_sigkill(fd):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    code = libc.syscall(424, ctypes.c_int(fd), ctypes.c_int(signal.SIGKILL), ctypes.c_void_p(), ctypes.c_uint(0))
    if code != 0:
        raise OSError(ctypes.get_errno(), 'pidfd signal failed; never retry')
    return dict(syscall=424, signal=int(signal.SIGKILL), returncode=0)

def exit_ready(fd):
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    rows = poller.poll(30000)
    if (len(rows) != 1 or rows[0][0] != fd or not rows[0][1] & select.POLLIN or
            rows[0][1] & ~(select.POLLIN | select.POLLHUP)):
        raise Refusal('positive pidfd exit readiness unavailable')
    return dict(pidfd_exit_ready=True, events=rows)

def acquire_root_lock():
    parent = directory(LOCK.parent)
    fd = None
    try:
        fd = os.open(LOCK.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent)
        meta = os.fstat(fd)
        linked = os.stat(LOCK.name, dir_fd=parent, follow_symlinks=False)
        if (not stat.S_ISREG(meta.st_mode) or (meta.st_dev, meta.st_ino) != (27, 4) or
                meta.st_uid != 0 or meta.st_gid != 0 or meta.st_nlink != 1 or
                stat.S_IMODE(meta.st_mode) != 0o644 or meta.st_size != 0 or
                (linked.st_dev, linked.st_ino) != (27, 4)):
            raise Refusal('preserved root lock identity differs')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result, fd = fd, None
        return result
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)

def quarantine_hold(lockfd):
    # No writer, diagnostic, signal handler or interrupted wait can return from
    # uncertain post-signal recovery. Reacquire the replacement flock if available.
    while True:
        if lockfd is None:
            try:
                lockfd = acquire_root_lock()
            except BaseException:
                pass
        try:
            if not os.path.lexists(QUARANTINE):
                publish(QUARANTINE, canonical(dict(status='RECOVERY_UNCERTAIN_ROOT_GUARD',
                                                  pid=os.getpid(), replacement_lock_held=lockfd is not None)))
        except BaseException:
            pass
        try:
            time.sleep(60)
        except BaseException:
            pass

def stable_record(row):
    path=Path(row['fd']['path'])
    observed,raw=file_identity(path,keep=True)
    meta=path.lstat()
    observed.update(mtime_ns=meta.st_mtime_ns,ctime_ns=meta.st_ctime_ns)
    if observed != row['fd']:
        raise Refusal('protected exact FD metadata/bytes drift: '+row['role'])
    archived,kept=file_identity(Path(row['raw_archive']['path']),keep=True)
    if archived['sha256']!=row['raw_archive']['sha256'] or archived['size']!=row['raw_archive']['bytes'] or kept!=raw:
        raise Refusal('preserved full raw record differs')
    return observed

def bind_current(release_path,checksum):
    release=read_json(release_path,checksum)
    if release.get('schema')!='mckernel.phase5.cleanup-holder-pidfd-release.v1' or release.get('status')!='PASS_EXECUTION_RELEASE' or release.get('execution_count')!=1 or type(release.get('execution_count')) is not int or release.get('signal_budget')!=1:
        raise Refusal('exact one-signal current recovery release required')
    if (os.getuid(),os.geteuid(),os.getgid(),os.getegid())!=(0,0,0,0) or os.uname().machine!='x86_64' or os.sched_getaffinity(0)!={7}:
        raise Refusal('reviewed root CPU7 target-holder recovery profile required')
    me=file_identity(SELF)[0]
    if release.get('source')!={'path':str(SELF),'sha256':me['sha256'],'bytes':me['size']}:
        raise Refusal('exact current recovery source differs')
    pointer=release['case'];case=read_json(Path(pointer['path']),pointer['sha256'])
    if pointer['sha256']!='14bb2eb47c5effc227f833dc9069c661a3a9081cc74e3dce29cee7095b95fb71' or case['bound_guard']['pid']!=PID or case['bound_guard']['starttime']!=START or case['bound_guard']['parent']!=PARENT or case['boot_id']!=BOOT:
        raise Refusal('historical/arbitrary recovery case forbidden')
    review=read_json(Path(release['execution_review']['path']),release['execution_review']['sha256'])
    payload={k:v for k,v in release.items() if k!='execution_review'}
    if review.get('decision')!='PASS_EXECUTION' or review.get('implementation_ownership') is not False or review.get('reviewed_release_payload_sha256')!=sha(canonical(payload)) or not review.get('reviewer') or review['reviewer']==release.get('author'):
        raise Refusal('genuine exact independent recovery release required')
    boot_check()
    state=strict(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
    if state.get('phase')!='running' or state.get('pause_reason') is not None or state.get('stop_reason') is not None or state['last_rate_limits']['primary']['usedPercent']>=100:
        raise Refusal('current launcher external/usage stop')
    for row in case['protected_raw_fd_records']:stable_record(row)
    for ref in case['closed_census']+[case['request']]:
        meta=file_identity(Path(ref['path']))[0]
        if meta['sha256']!=ref['sha256'] or meta['size']!=ref['bytes']:raise Refusal('closed positive census authority drift')
    for path in case['absent_before_effect']:
        if os.path.lexists(path):raise Refusal('precommon phase changed: '+path)
    return release,case

def retire_target(release_path,checksum):
    release,case=bind_current(release_path,checksum)
    if O.exists():raise Refusal('one-shot recovery already prepared; no automatic retry')
    O.mkdir(mode=0o700)
    requested=[];handlers={};pidfd=None;attempted=False;complete=False
    def defer(number,frame):
        if not requested:requested.append(number)
    previous=signal.pthread_sigmask(signal.SIG_BLOCK,DEFERRED_SIGNALS)
    try:
        for number in DEFERRED_SIGNALS:handlers[number]=signal.getsignal(number);signal.signal(number,defer)
        signal.pthread_sigmask(signal.SIG_SETMASK,previous)
        first=guard_identity(case);require_lock_holder(PID)
        if os.stat('/proc/%d/fd/3'%PID).st_dev!=27 or os.stat('/proc/%d/fd/3'%PID).st_ino!=4:raise Refusal('target exact fd3 permanent mutex differs')
        if proc_bytes('/proc/%d/task/%d/children'%(PID,PID)).strip():raise Refusal('target acquired descendants')
        pidfd=pidfd_open();bind_pidfd(pidfd,case)
        observed=[stable_record(row) for row in case['protected_raw_fd_records']]
        prepared={'status':'PREPARED_EXACT_CURRENT_PIDFD_RETIREMENT','case_sha256':release['case']['sha256'],'release_sha256':checksum,'signal_budget':1,'target':first,'protected_raw_records':observed,'original_build_status':'FAIL','shared_release_authorized':False}
        publish(O/'retire-target-prepared.json',canonical(prepared))
        bind_pidfd(pidfd,case);require_lock_holder(PID)
        if requested:raise Refusal('stop before sole signal')
        attempted=True
        signalled=sole_sigkill(pidfd);exited=exit_ready(pidfd)
        result={'status':'TARGET_PIDFD_EXIT_READY_PARENT_JOINS_REQUIRED','case_sha256':release['case']['sha256'],'sole_signal':signalled,'exit_proof':exited,'protected_raw_records':[stable_record(row) for row in case['protected_raw_fd_records']],'original_build_status':'FAIL','cleanup_required':True,'shared_release_authorized':False,'parent_direct_join_claim':False,'permanent_mutex_reacquisition_claim':False}
        publish(O/'retire-target-complete.json',canonical(result));complete=True;return result
    except BaseException as exc:
        try:publish(O/'retire-target-failure.json',canonical({'status':'RECOVERY_EXCEPTION_BEFORE_QUARANTINE','exception_type':type(exc).__name__,'message':str(exc)[:4096],'sole_signal_budget_consumed':attempted}))
        except BaseException:pass
        if attempted and not complete:quarantine_hold(None)
        raise
    finally:
        if pidfd is not None:os.close(pidfd)
        if not attempted or complete:
            signal.pthread_sigmask(signal.SIG_BLOCK,DEFERRED_SIGNALS)
            for number,handler in handlers.items():signal.signal(number,handler)
            signal.pthread_sigmask(signal.SIG_SETMASK,previous)

def verify_after_root_joins(release_path,checksum):
    release,case=bind_current(release_path,checksum)
    retired=read_json(O/'retire-target-complete.json')
    if retired.get('status')!='TARGET_PIDFD_EXIT_READY_PARENT_JOINS_REQUIRED' or retired.get('case_sha256')!=release['case']['sha256']:raise Refusal('positive exact pidfd exit missing')
    outer=read_json(Path(case['old_outer_status']));direct=read_json(Path(case['old_direct_join']))
    for row in (outer,direct):
        if row.get('direct_child_joined') is not True or row.get('pid')!=PARENT or str(row.get('proc_start_ticks'))!='29360713' or row.get('returncode')==0:raise Refusal('original sudo positive directwait identity/status missing')
    if outer.get('process_group_absent') is not True:raise Refusal('original cleanup process group not closed')
    for pid,row in case['original_processes'].items():
        try:fields=proc_stat(int(pid))
        except FileNotFoundError:continue
        if fields[19]==row['starttime']:raise Refusal('original target or parent still present after actual positive joins')
    rootfd=acquire_root_lock();txnfd=None
    try:
        require_lock_holder(os.getpid())
        row=case['transaction_lock'];txnfd=os.open(row['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
        meta=os.fstat(txnfd)
        if (meta.st_dev,meta.st_ino)!=(1828,116137):raise Refusal('same transaction mutex FD differs')
        fcntl.flock(txnfd,fcntl.LOCK_EX|fcntl.LOCK_NB);require_transaction_lock_holder(os.getpid())
        originals=[stable_record(row) for row in case['protected_raw_fd_records']]
        result={'status':'EXACT_HOLDER_PIDFD_EXIT_PARENT_JOINS_BOTH_MUTEXES_REACQUIRED_NO_RECORD_RELEASE','case_sha256':release['case']['sha256'],'outer_status':file_identity(Path(case['old_outer_status']))[0],'direct_wait':file_identity(Path(case['old_direct_join']))[0],'permanent_mutex':[27,4],'transaction_mutex':[1828,116137],'held_by_recovery_pid':os.getpid(),'protected_raw_records':originals,'build_status':'FAIL','shared_release_authorized':False,'cleanup_replay_authorized':False,'container_removal_authorized':False,'root_original_session_required_whole_joined':91614}
        publish(O/'after-parent-joins-and-both-mutexes.json',canonical(result));return result
    finally:
        if txnfd is not None:os.close(txnfd)
        os.close(rootfd)



def main():
    p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--release',type=Path,required=True);p.add_argument('--sha256',required=True);mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--retire-target',action='store_true');mode.add_argument('--verify-after-root-joins',action='store_true');a=p.parse_args()
    result=retire_target(a.release,a.sha256) if a.retire_target else verify_after_root_joins(a.release,a.sha256)
    print(json.dumps(result,sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
