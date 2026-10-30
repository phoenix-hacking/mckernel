"""Functional M14 owned control-process retirement; source only, no native cleanup."""
import fcntl
import hashlib
import json
import os
import select
import signal
import stat
import sys
import time
from pathlib import Path

BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1')
NONCE='dfd0a93f86905adc253dff7a4c83df722e498ba61d96c8fe524a6b7c3f2dacf0'
RES=BASE/'root-install-actual-caller-2'/'reservations'/('install-'+NONCE)
DIAG=BASE/'root-install-current-owned-metadata-1'/'actual-1'/'stdout.json'
DIAG_SHA='d92ce022653cf49796abee21fe49799b06bb57d9c158438f8e42bb87384a7814'
REQUEST_SHA='3923e78183ba15dd1b53e00753d0f6343c7e403ec6de2eb306b09c8cb333213a'
ARGV_SHA='c26900dfacbbd19ccaa8818d693322a59abf35f4640c000a54bd906171e3e824'
RES_SHA='0876dc7517a2d3ae4e64a2f2122c4ad095a25b92cd271f4b89d6c99f8ab09458'
PROFILE_SHA='af535cf3031e0aa7f955f72c0ffde7813eccd44b042bee1346f1b97970405eb9'
BOOT_SHA='7e2e05b2c19881ae4348b273e5eae7d734f199c93263219a2d0b49e2c763180c'
COMPAT_SHA='068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'
ROOT=3109451;ROOT_BIRTH='119988726';SUDO=3109448;SUDO_BIRTH='119988718';CALLER=3109447;CALLER_BIRTH='119988700'
OUTER=2996005;OUTER_BIRTH='118034116';UTC_CAP=1793774133*10**9
MAX=2*1024*1024
STOPS=(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM)
HELD=[]


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError('duplicate JSON key')
        result[k]=v
    return result


def bounded(path,limit):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size>limit:raise ValueError('bounded file')
        raw=b''
        while len(raw)<=limit:
            part=os.read(fd,min(65536,limit+1-len(raw)))
            if not part:break
            raw+=part
        after=os.fstat(fd)
        if len(raw)!=st.st_size or len(raw)>limit or (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('file changed')
        return raw
    finally:os.close(fd)


def proc_read(path,limit):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        chunks=[];total=0
        while total<=limit:
            part=os.read(fd,min(65536,limit+1-total))
            if not part:break
            chunks.append(part);total+=len(part)
        if total>limit:raise ValueError('proc read bound')
        return b''.join(chunks)
    finally:os.close(fd)


def checked(path,expected):
    raw=bounded(path,MAX)
    if sha(raw)!=expected:raise ValueError('bound evidence differs')
    return raw


def proc(pid):
    path=Path('/proc/%d'%pid)
    with (path/'stat').open('r') as stream:raw=stream.read(8193)
    if len(raw)>8192 or ')' not in raw:raise ValueError('proc stat bound')
    f=raw.rsplit(')',1)[1].split()
    if len(f)<20 or f[0] in ('Z','X','x'):raise ValueError('process not live')
    with (path/'comm').open('r') as stream:comm=stream.read(128).strip()
    return {'pid':pid,'birth':f[19],'ppid':int(f[1]),'pgrp':int(f[2]),'uid':os.stat(str(path)).st_uid,'comm':comm}


def require_root_session_ancestor():
    cursor=os.getppid();seen=set()
    for _ in range(32):
        if cursor<=1 or cursor in seen:break
        seen.add(cursor);row=proc(cursor)
        if cursor==OUTER:
            if row['birth']!=OUTER_BIRTH or row['uid']!=1000:raise ValueError('Root session identity changed')
            return
        cursor=row['ppid']
    raise ValueError('actual Root session ancestor absent')


def live_chain():
    a=proc(OUTER);b=proc(CALLER);c=proc(SUDO);d=proc(ROOT)
    if (a['birth']!=OUTER_BIRTH or a['uid']!=1000 or b['birth']!=CALLER_BIRTH or b['uid']!=1000 or b['ppid']!=OUTER or
        c['birth']!=SUDO_BIRTH or c['uid']!=0 or c['ppid']!=CALLER or c['comm']!='sudo' or
        d['birth']!=ROOT_BIRTH or d['uid']!=0 or d['ppid']!=SUDO or d['comm']!='python3'):
        raise ValueError('owned exact process chain changed')
    return {'outer':a,'caller':b,'sudo':c,'root':d}


def target_fds(diag):
    rows=[r for r in diag['targets'] if r['pid']==ROOT]
    if len(rows)!=1:raise ValueError('diagnostic target')
    expected=rows[0]['fd_metadata'];expected_by_fd={row['fd']:row for row in expected}
    if len(expected_by_fd)!=23 or any(row['target']=='<unlisted path redacted>' for row in expected):raise ValueError('diagnostic fd baseline')
    root=Path('/proc/%d'%ROOT);tasks=list((root/'task').iterdir())
    if len(tasks)!=1 or tasks[0].name!=str(ROOT):raise ValueError('target thread set changed')
    with (root/'task'/str(ROOT)/'children').open('r') as stream:children=stream.read(4097)
    if len(children)>4096 or children.strip():raise ValueError('target children present')
    current=list((root/'fd').iterdir())
    if len(current)!=len(expected_by_fd) or {int(x.name) for x in current}!=set(expected_by_fd):raise ValueError('target FD set changed')
    for item in current:
        n=int(item.name);before=expected_by_fd[n];target=os.readlink(str(item));st=os.stat(str(item))
        if target!=before['target'] or (st.st_dev,st.st_ino,stat.S_IFMT(st.st_mode))!=(before['device'],before['inode'],before['mode']):raise ValueError('target held FD changed')
        if target.startswith('/var/lib/mckernel-install-'+NONCE) or target.startswith('/var/lib/mckernel-code-'+NONCE):raise ValueError('operation path custody present')
    info=proc_read(Path('/proc/%d/fdinfo/23'%ROOT),65536).decode()
    fields=dict(line.split(':',1) for line in info.splitlines() if ':' in line)
    if fields.get('Pid','').strip()!='-1' or fields.get('NSpid','').strip()!='-1':raise ValueError('target retained child pidfd not terminal')
    for prefix in ('mckernel-install-','mckernel-code-'):
        if os.path.lexists('/var/lib/'+prefix+NONCE):raise ValueError('actual operation output exists')


def own_pidfd_identity(fd):
    raw=proc_read('/proc/self/fdinfo/%d'%fd,65536).decode()
    fields=dict(line.split(':',1) for line in raw.splitlines() if ':' in line)
    if fields.get('Pid','').strip()!=str(ROOT) or os.readlink('/proc/self/fd/%d'%fd)!='anon_inode:[pidfd]':raise ValueError('owned pidfd target differs')
    if not fcntl.fcntl(fd,fcntl.F_GETFD)&fcntl.FD_CLOEXEC:raise ValueError('pidfd CLOEXEC')


def elapsed(request):
    # The operation's first expired limit is enough; UTC weekly limit remains.
    return (time.clock_gettime_ns(time.CLOCK_BOOTTIME)>=request['deadline_boot_ns'] or
            time.monotonic_ns()>=request['deadline_mono_ns'] or time.time_ns()>=request['utc_cap_ns'])


def output(value):
    raw=canonical(value)
    if len(raw)>65536 or os.write(1,raw)!=len(raw):raise OSError('short outcome DATA')
    os.fsync(1)


def wait_terminal(fd,until):
    poll=select.poll();poll.register(fd,select.POLLIN|select.POLLHUP|select.POLLERR)
    while time.clock_gettime_ns(time.CLOCK_BOOTTIME)<until and time.time_ns()<UTC_CAP:
        events=poll.poll(100)
        if not events:continue
        mask=events[0][1]
        if mask&(select.POLLERR|select.POLLNVAL):raise ValueError('pidfd poll unknown')
        if mask&(select.POLLIN|select.POLLHUP):return True
    return False


def close_owned(record):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        if record['state']!='VERIFIED_HELD' or type(record['fd']) is not int:raise ValueError('pidfd not verified')
        fd=record['fd'];record['fd']=None;record['historical_fd']=fd;record['state']='CLOSING'
        try:os.close(fd)
        except BaseException:
            record['state']='CLOSURE_UNKNOWN';raise
        record['state']='VERIFIED_CLOSED'
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def run(compat,release,release_sha):
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={6}:raise ValueError('root/CPU6 stop owner required')
    capture=os.fstat(1);flags=fcntl.fcntl(1,fcntl.F_GETFL)
    if not stat.S_ISREG(capture.st_mode) or capture.st_nlink!=1 or (flags&os.O_ACCMODE)==os.O_RDONLY:raise ValueError('actual stdout capture required')
    require_root_session_ancestor()
    expected={'status':'REVIEWED_ONE_SHOT_OWNED_CONTROL_STOP','scope':'ROOT_INSTALL_CONTROL_ONLY','nonce':NONCE,
      'root_pid':ROOT,'root_birth':ROOT_BIRTH,'sudo_pid':SUDO,'sudo_birth':SUDO_BIRTH,'caller_pid':CALLER,'caller_birth':CALLER_BIRTH,
      'request_sha256':REQUEST_SHA,'argv_sha256':ARGV_SHA,'diagnostic_sha256':DIAG_SHA,'profile_sha256':PROFILE_SHA,
      'native_release':False,'native_currentfree':None,'reservation_release':False}
    if type(release) is not dict or set(release)!=set(expected)|{'issued_boot_ns','expires_boot_ns'} or sha(canonical(release))!=release_sha:raise ValueError('exact separately reviewed stop release required')
    issued=release['issued_boot_ns'];expires=release['expires_boot_ns'];now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if type(issued) is not int or type(expires) is not int or not issued<=now<expires<=issued+30000000000:raise ValueError('fresh reviewed stop release required')
    if canonical({k:release[k] for k in expected})!=canonical(expected):raise ValueError('stop release scope differs')
    request=json.loads(checked(RES/'request.json',REQUEST_SHA),object_pairs_hook=unique)
    reservation=json.loads(checked(RES/'RESERVATION.json',RES_SHA),object_pairs_hook=unique)
    argv=json.loads(checked(RES/'argv.json',ARGV_SHA),object_pairs_hook=unique)
    diag=json.loads(checked(DIAG,DIAG_SHA),object_pairs_hook=unique)
    if (request.get('nonce')!=NONCE or request.get('profile_sha256')!=PROFILE_SHA or reservation.get('nonce')!=NONCE or
        reservation.get('status')!='RESERVED_UNKNOWN_UNTIL_ROOT_JOIN' or reservation.get('reservation_release',False) is not False):raise ValueError('retained reservation differs')
    if type(argv) is not list or len(argv)!=22 or sha(argv[16].encode())!=BOOT_SHA or argv[12:16]!=['/usr/bin/python3','-I','-B','-c']:raise ValueError('reviewed operation argv')
    if not elapsed(request) or time.time_ns()>=UTC_CAP:raise ValueError('operation cap not expired or weekly cap ended')
    # Verify source/argv and exact retained custody before opening a pidfd.
    live_chain();target_fds(diag)
    cmd=proc_read('/proc/%d/cmdline'%ROOT,262144)
    if cmd!=b'\0'.join(os.fsencode(x) for x in argv[12:])+b'\0':raise ValueError('actual root bootstrap argv differs')
    exe=os.open('/proc/%d/exe'%ROOT,os.O_RDONLY|os.O_CLOEXEC)
    try:
        st=os.fstat(exe);system=os.stat('/usr/bin/python3')
        if (st.st_dev,st.st_ino)!=(system.st_dev,system.st_ino) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022:raise ValueError('root interpreter identity')
        h=hashlib.sha256();total=0
        while True:
            part=os.read(exe,65536)
            if not part:break
            total+=len(part)
            if total>128*1024*1024:raise ValueError('interpreter byte bound')
            h.update(part)
        expected_runtime=request['owner_release']['creation_model_approval']['runtime_sha256']
        if h.hexdigest()!=expected_runtime:raise ValueError('root interpreter bytes differ')
    finally:os.close(exe)
    live_chain();target_fds(diag)
    record={'state':'REGISTERED','fd':None,'historical_fd':None};HELD.append(record)
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        try:fd=compat.open_pidfd(ROOT,0)
        except compat.PidfdVerificationError as error:
            record['fd']=error.fd;record['state']='UNKNOWN_RETAINED';raise
        record['fd']=fd;record['state']='PIDFD_OPENED'
        own_pidfd_identity(fd);record['state']='VERIFIED_HELD'
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
    # Kernel pins exact process; recheck chain and actual custody immediately.
    live_chain();target_fds(diag);own_pidfd_identity(fd)
    if not elapsed(request) or time.time_ns()>=UTC_CAP or time.clock_gettime_ns(time.CLOCK_BOOTTIME)>=expires:raise ValueError('stop cap or weekly clock changed')
    start=time.clock_gettime_ns(time.CLOCK_BOOTTIME);term_until=min(start+3000000000,expires);end=min(start+8000000000,expires)
    record['signal_phase']='TERM_IN_PROGRESS'
    compat.send_signal(fd,signal.SIGTERM);record['signal_phase']='TERM_SENT'
    terminated=wait_terminal(fd,term_until);used_kill=False
    if not terminated:
        terminated=wait_terminal(fd,min(end,time.clock_gettime_ns(time.CLOCK_BOOTTIME)+100000000))
    if not terminated:
        own_pidfd_identity(fd)
        if time.clock_gettime_ns(time.CLOCK_BOOTTIME)>=end or time.time_ns()>=UTC_CAP:raise TimeoutError('no escalation time')
        record['signal_phase']='KILL_IN_PROGRESS'
        compat.send_signal(fd,signal.SIGKILL);record['signal_phase']='KILL_SENT';used_kill=True;terminated=wait_terminal(fd,end)
    if not terminated:raise TimeoutError('target terminal unproved')
    record['signal_phase']='TARGET_TERMINAL'
    output({'status':'TARGET_PIDFD_TERMINAL','nonce':NONCE,'target_pid':ROOT,'target_birth':ROOT_BIRTH,'kill_used':used_kill,
            'direct_wait':'NOT_OWNER','native_release':False,'native_currentfree':None,'reservation_release':False})
    close_owned(record)
    output({'status':'CONTROL_STOP_COMPLETE_PIDFD_CLOSED','nonce':NONCE,'target_pid':ROOT,'target_birth':ROOT_BIRTH,
            'pidfd_disposition':record['state'],'caller_sudo_join':'NOT_OBSERVED','native_release':False,'native_currentfree':None,'reservation_release':False})
    return record


def guarded_run(compat,release,release_sha):
    try:return run(compat,release,release_sha)
    except BaseException as error:
        record=HELD[-1] if HELD else None
        state=None if record is None else record.get('state')
        phase='BEFORE_PIDFD' if record is None else record.get('signal_phase','BEFORE_SIGNAL')
        try:output({'status':'CONTROL_STOP_UNKNOWN','nonce':NONCE,'target_pid':ROOT,'target_birth':ROOT_BIRTH,
             'signal_phase':phase,'pidfd_disposition':state,'error_type':type(error).__name__,
             'native_release':False,'native_currentfree':None,'reservation_release':False})
        except BaseException:pass
        if record is not None and record.get('fd') is not None:
            # Never discard or reclose an uncertain owned target handle.
            while True:time.sleep(1)
        raise
