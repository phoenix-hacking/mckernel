"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Copied retained OFD predicates, retargeted fixed O_RDWR growth description only.
"""
import fcntl,os,select,stat
from pathlib import Path
FIELDS=('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
def need(ok,reason):
    if not ok:raise ValueError(reason)

def rows(pid,fd):
    return [line.split()[2:] for line in Path('/proc/%d/fdinfo/%d'%(pid,fd)).read_text().splitlines() if line.startswith('lock:')]

def metadata(value):return {key:getattr(value,key) for key in FIELDS}

def rdwr_private(pid,fd):
    report=Path('/proc/%d/fdinfo/%d'%(pid,fd)).read_text()
    flags=[line.split()[1] for line in report.splitlines() if line.startswith('flags:')]
    need(len(flags)==1,'custody-fdinfo-flags')
    value=int(flags[0],8)
    need(value&os.O_ACCMODE==os.O_RDWR and value&os.O_CLOEXEC,'custody-private-rdwr-fdinfo')

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
    need(fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_ACCMODE==os.O_RDWR and not os.get_inheritable(fd),'custody-private-rdwr-copy')
    rdwr_private(holder_pid,holder_fd)
    key='{:02x}:{:02x}:{}'.format(os.major(before.st_dev),os.minor(before.st_dev),before.st_ino)
    wanted=['FLOCK','ADVISORY','WRITE',str(lock_origin_pid),key,'0','EOF']
    need(rows(os.getpid(),fd)==[wanted] and rows(holder_pid,holder_fd)==[wanted],'custody-same-description-original-origin')
    global_rows=[line.split()[1:] for line in Path('/proc/locks').read_text().splitlines() if key in line.split()]
    need(global_rows==[wanted],'custody-global-exclusive-original-origin')
    need(metadata(os.fstat(fd))==expected_metadata==metadata(os.stat(path,follow_symlinks=False))==metadata(os.stat(remote)),'custody-descriptor-or-name-raced')
    return dict(same_description_observed=True,holder_pid=holder_pid,holder_fd=holder_fd,
                lock_origin_pid=lock_origin_pid,retained_fd=fd,lock=wanted,device=before.st_dev,inode=before.st_ino,
                retirement_authority=False,fresh_root_actor_binding=False)

def process(pid,start,parent,pgid,credentials,command):
    raw=Path('/proc/%d/stat'%pid).read_bytes();left,sep,right=raw.rpartition(b') ');fields=right.split()
    need(sep and left.startswith(str(pid).encode()+b' (') and len(fields)>=50 and fields[0] not in (b'Z',b'X',b'x',b'T',b't')
         and fields[19].decode()==start and (int(fields[1]),int(fields[2]))==(parent,pgid),'successor-exact-live-actor-birth-lineage')
    report=Path('/proc/%d/status'%pid).read_text()
    actual={line.split(':',1)[0]:line.split()[1:] for line in report.splitlines() if line.startswith(('Uid:','Gid:'))}
    need(actual=={'Uid':[str(credentials)]*4,'Gid':[str(credentials)]*4},'successor-actor-credentials')
    need(Path('/proc/%d/cmdline'%pid).read_bytes()==command,'successor-exact-source-granted-argv')
    return dict(pid=pid,starttime=start,parent=parent,pgid=pgid,command_hex=command.hex(),credentials=actual)

def verify_held_after_exit(fd,pidfd,expected_metadata,path,lock_origin_pid=1281419):
    """Postexit copy predicate only; external real joins/absence remain required."""
    poll=select.poll();poll.register(pidfd,select.POLLIN)
    need(any(f==pidfd and mask&select.POLLIN for f,mask in poll.poll(0)),'successor-positive-predecessor-pidfd-exit')
    need(metadata(os.fstat(fd))==expected_metadata==metadata(os.stat(path,follow_symlinks=False)),'successor-held-metadata')
    need(fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_ACCMODE==os.O_RDWR and not os.get_inheritable(fd),'successor-held-private-rdwr-copy')
    value=os.fstat(fd);key='{:02x}:{:02x}:{}'.format(os.major(value.st_dev),os.minor(value.st_dev),value.st_ino)
    wanted=['FLOCK','ADVISORY','WRITE',str(lock_origin_pid),key,'0','EOF']
    need(rows(os.getpid(),fd)==[wanted],'successor-postexit-original-origin-fdinfo')
    need([line.split()[1:] for line in Path('/proc/locks').read_text().splitlines() if key in line.split()]==[wanted],'successor-postexit-original-origin-global')
    need(metadata(os.fstat(fd))==expected_metadata==metadata(os.stat(path,follow_symlinks=False)),'successor-held-metadata-raced')
    return True
