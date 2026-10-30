#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root direct parent for the fixed read-only daemon metadata reader; no Docker query.
"""
import ast,fcntl,hashlib,json,os,resource,signal,stat,subprocess,sys,time
from pathlib import Path

READER=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-nonheld13-owner-source-1/sdk13_daemon_metadata_reader.v4.py')
READER_SHA='ef5eadb127f024275e10cbe2d4c8b2f2a8cf1a3fe301a20cd7d23a627df1d9f8'
CENSUS=Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-sdk-20261019-1/capsule/scripts/native_rust_exact_build_container_owner.py')
CENSUS_SHA='96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1'
PYTHON='/home/holden/anaconda3/bin/python3.9'

def proc_identity(pid):
    raw=Path('/proc',str(pid),'stat').read_text()
    if len(raw)>65536:raise ValueError('oversized stat')
    f=raw.rsplit(')',1)[1].split()
    return {'pid':pid,'birth':int(f[19]),'ppid':int(f[1]),'pgid':int(f[2]),'sid':int(f[3])}

def verified_source(path,sha):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        a=os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or a.st_size>1024*1024:raise ValueError('source type/size mismatch')
        chunks=[];n=0
        while True:
            z=os.read(fd,65536)
            if not z:break
            n+=len(z)
            if n>1024*1024:raise ValueError('source growth')
            chunks.append(z)
        c=os.fstat(fd); named=os.lstat(path)
        keys=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')
        if n!=a.st_size or any(getattr(a,k)!=getattr(c,k) or getattr(a,k)!=getattr(named,k) for k in keys):raise ValueError('source drift')
        raw=b''.join(chunks)
        if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('source hash mismatch')
        return raw
    finally:os.close(fd)

def members(pgid):
    raw=verified_source(CENSUS,CENSUS_SHA);tree=ast.parse(raw,str(CENSUS))
    cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Docker')
    fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='_surviving_group_members')
    env={'Path':Path};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(CENSUS),'exec'),env)
    ctx=type('CensusContext',(),{})();ctx.client_retirement_unproven=False
    values=env[fn.name](ctx,pgid)
    if ctx.client_retirement_unproven:raise ValueError('group observation uncertainty')
    return sorted(values)

def terminal(pid):return os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None

def child_limits():
    resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
    resource.setrlimit(resource.RLIMIT_CPU,(10,10))

def main():
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={7}:raise ValueError('root CPU7 required')
    parent=proc_identity(os.getpid());raw=verified_source(READER,READER_SHA)
    fd=os.memfd_create('sdk13-fixed-daemon-reader',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
    try:
        offset=0
        while offset<len(raw):
            n=os.write(fd,raw[offset:])
            if n<=0:raise OSError('short immutable reader write')
            offset+=n
        os.lseek(fd,0,os.SEEK_SET)
        seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL
        fcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)
        if fcntl.fcntl(fd,fcntl.F_GET_SEALS)!=seals:raise ValueError('reader memfd seal mismatch')
        proc=subprocess.Popen([PYTHON,'-I','-B','/proc/self/fd/%d'%fd],stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
                              env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','LC_ALL':'C'},
                              pass_fds=(fd,),preexec_fn=child_limits)
    finally:os.close(fd)
    child=None;waited=None;waitstatus=None;error=None;out=b'';err=b'';closed=False;group_absent=False
    try:
        child=proc_identity(proc.pid)
        if child['ppid']!=parent['pid'] or child['pgid']!=child['pid'] or child['sid']!=child['pid']:raise ValueError('reader identity mismatch')
        until=time.monotonic()+10
        while not terminal(proc.pid):
            if time.monotonic()>=until:raise TimeoutError('reader timeout')
            time.sleep(.01)
    except BaseException as exc:
        error=type(exc).__name__+': '+str(exc)
        # The unreaped direct child is the only permissible signal target.
        try:
            if child is not None and proc_identity(proc.pid)==child:
                os.kill(proc.pid,signal.SIGTERM);limit=time.monotonic()+1
                while not terminal(proc.pid) and time.monotonic()<limit:time.sleep(.01)
                if not terminal(proc.pid) and proc_identity(proc.pid)==child:os.kill(proc.pid,signal.SIGKILL)
        except (OSError,ValueError,IndexError):pass
    try:
        limit=time.monotonic()+2
        while not terminal(proc.pid) and time.monotonic()<limit:time.sleep(.01)
        if terminal(proc.pid):
            waited,waitstatus,_=os.wait4(proc.pid,0);proc.returncode=os.waitstatus_to_exitcode(waitstatus)
        if waited==proc.pid:
            out=proc.stdout.read(8193);err=proc.stderr.read(8193)
            if len(out)>8192 or len(err)>8192:raise ValueError('reader output bound')
            proc.stdout.close();proc.stderr.close();closed=True
            group_absent=not members(proc.pid)
    except BaseException as exc:error=(error or '')+'; join '+type(exc).__name__+': '+str(exc)
    result={'status':'UNKNOWN_DAEMON_PARENT','parent':parent,'reader':child,'reader_wait4_pid':waited,
            'reader_wait4_status':waitstatus,'reader_direct_joined':waited==proc.pid,'reader_group_absent':group_absent,
            'reader_streams_closed':closed,'error':error,'current_free':False}
    if not error and waited==proc.pid and proc.returncode==0 and closed and group_absent:
        try:
            sample=json.loads(out)
            if sample.get('status')!='OBSERVED_EXACT_DAEMON_READONLY' or sample.get('reader')!=child:raise ValueError('reader result identity mismatch')
            result.update(status='PASS_EXACT_DAEMON_METADATA',sample=sample)
        except BaseException as exc:result['error']=type(exc).__name__+': '+str(exc)
    print(json.dumps(result,sort_keys=True),flush=True)
    return 0 if result['status']=='PASS_EXACT_DAEMON_METADATA' else 2

if __name__=='__main__':
    try:code=main()
    except BaseException as exc:
        print(json.dumps({'status':'UNKNOWN_DAEMON_PARENT','error':type(exc).__name__+': '+str(exc),
                          'current_free':False},sort_keys=True),flush=True);sys.exit(2)
    sys.exit(code)
