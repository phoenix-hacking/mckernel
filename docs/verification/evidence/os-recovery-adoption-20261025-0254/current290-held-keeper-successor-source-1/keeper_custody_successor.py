"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Unreleased closed successor adapter. Definitions only; no production acquisition,
signals, release, transaction mutation, CLI or automatic retry on import.
"""
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import types

SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
E = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
OLD = E / 'current290-partial-quarantine-reconciliation-source-1'
CAPTURE = E / 'ROOT-NEW18H-PARTIAL-CUSTODY-PREPARATION-1'
PID, START, PARENT, PARENT_START, PGID, TARGET_FD = 1193473, '83392603', 1193470, '83392595', 1193468, 6
LOCK_ORIGIN_PID = 1060806
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
ADAPTER = 'exact-held-keeper1193473-fd6-origin1060806-v1'
FIELDS = ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
PINS = {
 'adoption': (OLD/'partial_quarantine_adoption.py', 13459, '57722eab94b8494c2423cf9a161ff43ed2948018fa0ddc8ad59f91cd9d9968aa'),
 'runtime': (OLD/'keeper-capture-shared-mutator-source-1/runtime_pipeline.py',33739,'0a67af9b28ac480960dbcaa2553b9b262cf90f1f96618beb818392018715648c'),
 'entry': (OLD/'keeper-capture-shared-mutator-source-1/capture_entry.py',11236,'58c80704920fec383a2ec19bf1594a6b24a57688be681232d140dbaa55d26497'),
 'outer': (OLD/'keeper-capture-shared-mutator-source-1/capture_outer.py',9167,'3d3e46527400d7142a9c98dfa63f665d9973057526dce66b39417ac2e71800c4'),
 'launch': (CAPTURE/'LAUNCH-PACKET.json',5009,'4b12ca19177fcc5e5269608217286dbb01104a141570e79e14413429a9d5bfcf'),
 'authorization': (CAPTURE/'LAUNCH-AUTHORIZATION.json',572,'3668426712e1a080f3232288412b987c2f0b69a2d9223c6dc753587cfa571b8d'),
 'process': (CAPTURE/'RUNTIME/PROCESS.json',2403,'630b426e3f402dc3311be298efeabee9fdd05560b38cb7c9bd45e6a38c9eb63d'),
 'entry_process': (CAPTURE/'ENTRY/ENTRY-PROCESS.json',2804,'04dea9c0a1e18f2519d5919a32bc41ff21addbff046c0a3e423ee257d512a35d'),
 'sudo_birth': (CAPTURE/'OUTER/DIRECT-CHILD-BIRTH.json',2820,'44fc48dba835613b85a15f757b2a17d62a161c5356d00bff87a4d5c3428db90f'),
 'outer_process': (CAPTURE/'OUTER/OUTER-PROCESS.json',2344,'6a2626eca9ff456c4f99e04c1c84b35c788100bf40b0b26966e3dfbea3e33836')}

def need(ok, reason):
    if not ok: raise ValueError(reason)
def pinned(name):
    path,size,digest=PINS[name]; raw=path.read_bytes()
    need(len(raw)==size and hashlib.sha256(raw).hexdigest()==digest,'successor-input-pin:'+name)
    return raw
def source(name):
    module=types.ModuleType('_successor_'+name);module.__file__=str(PINS[name][0])
    exec(compile(pinned(name),module.__file__,'exec'),module.__dict__)
    return module
def rows(pid,fd):
    return [line.split()[2:] for line in Path('/proc/%d/fdinfo/%d'%(pid,fd)).read_text().splitlines() if line.startswith('lock:')]
def metadata(value):return {key:getattr(value,key) for key in FIELDS}
def readonly_private(pid,fd):
    report=Path('/proc/%d/fdinfo/%d'%(pid,fd)).read_text()
    flags=[line.split()[1] for line in report.splitlines() if line.startswith('flags:')]
    need(len(flags)==1,'custody-fdinfo-flags')
    value=int(flags[0],8)
    need(value&os.O_ACCMODE==os.O_RDONLY and value&os.O_CLOEXEC,'custody-private-readonly-fdinfo')

def verify_custody(fd,holder_pid,holder_fd,path,expected_metadata,lock_origin_pid):
    """Genuine copied OFD predicate: current holder and immutable origin differ.
    Acquisition must independently be genuine dup/pidfd_getfd; reopening is refused.
    Caller retains fd throughout; this function performs no close/unlock/signal.
    """
    before=os.fstat(fd); named=os.stat(path,follow_symlinks=False)
    remote=Path('/proc/%d/fd/%d'%(holder_pid,holder_fd))
    held=os.stat(remote)
    need(metadata(before)==expected_metadata==metadata(named)==metadata(held)
         and stat.S_ISREG(before.st_mode) and before.st_size==0 and before.st_nlink==1,'custody-fd-name-holder-metadata')
    need(fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_ACCMODE==os.O_RDONLY and not os.get_inheritable(fd),'custody-private-readonly-copy')
    readonly_private(holder_pid,holder_fd)
    key='{:02x}:{:02x}:{}'.format(os.major(before.st_dev),os.minor(before.st_dev),before.st_ino)
    wanted=['FLOCK','ADVISORY','WRITE',str(lock_origin_pid),key,'0','EOF']
    need(rows(os.getpid(),fd)==[wanted] and rows(holder_pid,holder_fd)==[wanted],'custody-same-description-original-origin')
    global_rows=[line.split()[1:] for line in Path('/proc/locks').read_text().splitlines() if key in line.split()]
    need(global_rows==[wanted],'custody-global-exclusive-original-origin')
    need(metadata(os.fstat(fd))==expected_metadata==metadata(os.stat(path,follow_symlinks=False))==metadata(os.stat(remote)),'custody-descriptor-or-name-raced')
    return dict(same_description_observed=True,holder_pid=holder_pid,holder_fd=holder_fd,
                lock_origin_pid=lock_origin_pid,retained_fd=fd,lock=wanted,device=before.st_dev,inode=before.st_ino,
                retirement_authority=False,fresh_root_actor_binding=False)

def verify_description_custody(fd,holder_pid,holder_fd,path,expected_metadata):
    need((holder_pid,holder_fd,Path(path))==(PID,TARGET_FD,Path('/run/lock/mckernel-development.lock')),'closed-successor-custody-target')
    return verify_custody(fd,holder_pid,holder_fd,path,expected_metadata,LOCK_ORIGIN_PID)

def adoption():
    module=source('adoption')
    module.verify_description_custody=verify_description_custody
    return module

def authenticate_predecessor():
    """Saved evidence binding only; never grants fresh execution authority."""
    entry=source('entry'); raw=pinned('launch'); packet=entry.parse(raw)
    entry.verify_sources(packet,here=PINS['entry'][0].parent)
    envelope=entry.parse(pinned('authorization'))
    entry.verify_authorization(packet,raw,PINS['launch'][0],envelope)
    proc=entry.parse(pinned('process')); ep=entry.parse(pinned('entry_process')); op=entry.parse(pinned('outer_process'))
    need(proc['keeper']==dict(pid=PID,starttime=START,pgid=PGID)==ep['process'].__class__(
         (k,ep['process'][k]) for k in ('pid','starttime','pgid')),'retained-keeper-birth')
    need(proc['command_hex']==ep['process']['command_hex'] and proc['launch_sha256']==PINS['launch'][2]
         and proc['source_hashes']==packet['source_hashes'] and proc['old_actor']==packet['old_actor'],'retained-keeper-source-grant')
    need(op['process']['pid']==1193469 and op['process']['starttime']=='83392586' and op['process']['pgid']==PGID,'retained-outer-birth')
    for name in ('runtime','entry','outer'):pinned(name)
    payload=entry.payload_argv(PINS['launch'][0],PINS['launch'][2],packet)+[
      '--authorization',str(PINS['authorization'][0]),'--authorization-sha256',PINS['authorization'][2]]
    expected=b'\0'.join(x.encode() for x in payload)+b'\0'
    need(expected.hex()==proc['command_hex'],'retained-root-exact-granted-argv')
    sudo=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit',
          '--as=2147483648:2147483648','--fsize=33554432:33554432','--core=0:0','--']+payload
    birth=entry.parse(pinned('sudo_birth'))
    need(birth['process']['pid']==PARENT and birth['process']['starttime']==PARENT_START
         and birth['process']['ppid']==1193469 and birth['process']['pgid']==PGID
         and birth['observation']=='blocked-before-exec' and birth['planned_exec_argv']==sudo,
         'retained-sudo-birth-and-exact-planned-granted-exec')
    return expected,b'\0'.join(x.encode() for x in sudo)+b'\0',bytes.fromhex(op['process']['command_hex'])

def process(pid,start,parent,pgid,credentials,command):
    raw=Path('/proc/%d/stat'%pid).read_bytes();left,sep,right=raw.rpartition(b') ');fields=right.split()
    need(sep and left.startswith(str(pid).encode()+b' (') and len(fields)>=50 and fields[0] not in (b'Z',b'X',b'x',b'T',b't')
         and fields[19].decode()==start and (int(fields[1]),int(fields[2]))==(parent,pgid),'successor-exact-live-actor-birth-lineage')
    report=Path('/proc/%d/status'%pid).read_text()
    actual={line.split(':',1)[0]:line.split()[1:] for line in report.splitlines() if line.startswith(('Uid:','Gid:'))}
    need(actual=={'Uid':[str(credentials)]*4,'Gid':[str(credentials)]*4},'successor-actor-credentials')
    need(Path('/proc/%d/cmdline'%pid).read_bytes()==command,'successor-exact-source-granted-argv')
    return dict(pid=pid,starttime=start,parent=parent,pgid=pgid,command_hex=command.hex(),credentials=actual)

def actor_binding(p):
    need(os.getuid()==os.geteuid()==0 and os.uname().machine=='x86_64','successor-root-x86_64-only')
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'successor-exact-boot')
    child,sudo,outer=authenticate_predecessor()
    return (process(PID,START,PARENT,PGID,0,child),
            process(PARENT,PARENT_START,1193469,PGID,0,sudo),
            process(1193469,'83392586',1193468,PGID,1000,outer))

def live_pidfd(p,pidfd):
    raw=Path('/proc/self/fdinfo/%d'%pidfd).read_text()
    need([line.split()[1:] for line in raw.splitlines() if line.startswith('Pid:')]==[[str(PID)]],'successor-exact-pidfd-target')
    poll=select.poll();poll.register(pidfd,select.POLLIN|select.POLLHUP|select.POLLERR)
    need(poll.poll(0)==[],'successor-pidfd-target-not-live')

class Standby:
    def __init__(self,fd,pidfd):
        self.fd,self.pidfd=fd,pidfd
        self.verified,self.error,self.proof=False,None,None

def acquire_exact_standby():
    """Unreleased callable: copies ONLY live keeper1193473 FD6, never lock anew.
    Failure after successful getfd returns a retained hold, never closes custody.
    Separate launch/review plus actual resource admission are required externally.
    """
    p=adoption();before=actor_binding(p);meta=metadata(os.stat(p.ROOT_MUTEX,follow_symlinks=False))
    need(tuple(meta[k] for k in ('st_dev','st_ino','st_uid','st_gid','st_nlink','st_size','st_mode'))==(27,4,0,0,1,0,0o100644),'successor-permanent-node')
    libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long
    pidfd=libc.syscall(ctypes.c_long(434),ctypes.c_int(PID),ctypes.c_uint(0))
    if pidfd<0:raise OSError(ctypes.get_errno(),'successor-pidfd-open-no-fallback')
    try:
        live_pidfd(p,pidfd);need(actor_binding(p)==before,'successor-before-getfd-race')
        fd=libc.syscall(ctypes.c_long(438),ctypes.c_int(pidfd),ctypes.c_int(TARGET_FD),ctypes.c_uint(0))
        if fd<0:raise OSError(ctypes.get_errno(),'successor-pidfd-getfd-no-fallback')
    except BaseException:
        os.close(pidfd);raise
    hold=Standby(fd,pidfd)
    try:
        live_pidfd(p,pidfd);need(actor_binding(p)==before,'successor-after-getfd-race')
        custody=verify_description_custody(fd,PID,TARGET_FD,p.ROOT_MUTEX,meta)
        live_pidfd(p,pidfd);need(actor_binding(p)==before,'successor-final-actor-race')
        hold.proof=dict(scope=SCOPE,custody_adapter=ADAPTER,old_actor=p.ROOT_ACTOR,
            predecessor_custodian=dict(pid=PID,starttime=START,parent=PARENT,pgid=PGID,fd=TARGET_FD,boot_id=BOOT),
            custody=custody,positive_pidfd_target_alive=True,actor_birth_rechecked=True,
            predecessor_launch_sha256=PINS['launch'][2],actual_retirement=False,
            quarantine_untouched=True,runtime_execution_release=False,requires_live_keeper=True)
        hold.verified=True
    except BaseException as error:hold.error=type(error).__name__+': '+str(error)
    return hold

def verify_held_after_exit(fd,pidfd,expected_metadata,path,lock_origin_pid=LOCK_ORIGIN_PID):
    """Postexit copy predicate only; external real joins/absence remain required."""
    poll=select.poll();poll.register(pidfd,select.POLLIN)
    need(any(f==pidfd and mask&select.POLLIN for f,mask in poll.poll(0)),'successor-positive-predecessor-pidfd-exit')
    need(metadata(os.fstat(fd))==expected_metadata==metadata(os.stat(path,follow_symlinks=False)),'successor-held-metadata')
    need(fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_ACCMODE==os.O_RDONLY and not os.get_inheritable(fd),'successor-held-private-readonly-copy')
    value=os.fstat(fd);key='{:02x}:{:02x}:{}'.format(os.major(value.st_dev),os.minor(value.st_dev),value.st_ino)
    wanted=['FLOCK','ADVISORY','WRITE',str(lock_origin_pid),key,'0','EOF']
    need(rows(os.getpid(),fd)==[wanted],'successor-postexit-original-origin-fdinfo')
    need([line.split()[1:] for line in Path('/proc/locks').read_text().splitlines() if key in line.split()]==[wanted],'successor-postexit-original-origin-global')
    need(metadata(os.fstat(fd))==expected_metadata==metadata(os.stat(path,follow_symlinks=False)),'successor-held-metadata-raced')
    return True

if __name__=='__main__':raise SystemExit('SOURCE ONLY: no independently released successor launch or operation')
