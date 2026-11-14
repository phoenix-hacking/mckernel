#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root direct parent for the fixed read-only daemon metadata reader; no Docker query.
"""
import ast,base64,fcntl,hashlib,json,os,resource,signal,stat,subprocess,sys,time
from pathlib import Path

READER=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-nonheld13-owner-source-1/sdk13_daemon_metadata_reader.v4.py')
READER_SHA='ef5eadb127f024275e10cbe2d4c8b2f2a8cf1a3fe301a20cd7d23a627df1d9f8'
CENSUS=Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-sdk-20261019-1/capsule/scripts/native_rust_exact_build_container_owner.py')
CENSUS_SHA='96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1'
PYTHON='/home/holden/anaconda3/bin/python3.9'

ROOT=READER.parent
RELEASE=ROOT/'ROOT-SDK13-DATA32-RELEASE.ACTUAL.json'
CONTROLS=ROOT.parent/'ACTUAL-CONTROLS-ARMED.json'
CAPACITY=ROOT.parent/'ACTUAL-CAPACITY-FALLBACK-ARMED.json'
UTC_LIMIT=1793774133
BOOT_LIMIT=1571569.6959267766
MONO_LIMIT=1556231.5688797957
BOOT_ID='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
STOP_SIGNALS={signal.SIGTERM,signal.SIGINT,signal.SIGALRM}
stopping=False

def stop(signum,frame):
    global stopping
    stopping=True

def bound_document(path,expected,root=False):
    if not isinstance(expected,list) or len(expected)!=8:raise ValueError('sealed identity token malformed')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        a=os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or a.st_size>2**20 or (root and (a.st_uid!=0 or stat.S_IMODE(a.st_mode)&0o077)):
            raise ValueError('sealed document identity mismatch')
        chunks=[];size=0
        while True:
            z=os.read(fd,65536)
            if not z:break
            size+=len(z)
            if size>2**20:raise ValueError('sealed document growth')
            chunks.append(z)
        c=os.fstat(fd);named=os.lstat(path);keys=('st_dev','st_ino','st_mode','st_uid','st_size','st_mtime_ns','st_ctime_ns')
        if size!=a.st_size or any(getattr(a,k)!=getattr(c,k) or getattr(a,k)!=getattr(named,k) for k in keys):raise ValueError('sealed document changed')
        raw=b''.join(chunks);actual=[a.st_dev,a.st_ino,a.st_mode,a.st_uid,a.st_size,a.st_mtime_ns,a.st_ctime_ns,hashlib.sha256(raw).hexdigest()]
        if actual!=expected:raise ValueError('sealed document bytes/identity drift')
        return json.loads(raw)
    finally:os.close(fd)

def parent_effect_gate(token):
    if stopping or signal.sigpending() & STOP_SIGNALS:raise InterruptedError('stop before reader spawn')
    if not isinstance(token,dict) or set(token)!={'release','controls'} or not isinstance(token['controls'],list) or len(token['controls'])!=2:
        raise ValueError('reader authority token malformed')
    release=bound_document(RELEASE,token['release'],root=True)
    for path,identity in zip((CONTROLS,CAPACITY),token['controls']):
        doc=bound_document(path,identity)
        if doc.get('caps')!={'boot_deadline':BOOT_LIMIT,'boot_id':BOOT_ID,'deadline':UTC_LIMIT,'monotonic_deadline':MONO_LIMIT}:
            raise ValueError('reader control caps differ')
    facts=release.get('admission')
    if not isinstance(facts,dict) or facts.get('service_status')!='NO_NEW_REJECTION' or facts.get('paid_fallback') is not False:
        raise ValueError('reader service/billing status missing')
    used=facts.get('weekly_used_percent');observed=facts.get('weekly_observed_utc');expiry=facts.get('expiry_utc')
    current_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    now=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic()
    if (type(used) not in (int,float) or not 0<=used<100 or type(observed) not in (int,float) or not 0<=now-observed<=30 or
        type(expiry) not in (int,float) or not now<expiry<=UTC_LIMIT or now>=UTC_LIMIT or boot>=BOOT_LIMIT or mono>=MONO_LIMIT or
        current_boot_id!=BOOT_ID):
        raise ValueError('reader usage or time ceiling expired')
    if stopping or signal.sigpending() & STOP_SIGNALS:raise InterruptedError('stop before reader spawn')
    return {'utc':now,'boot':boot,'mono':mono,'weekly_observed_utc':observed,'expiry_utc':expiry}

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


def bounded_stream(stream,limit):
    data=bytearray();error=None;complete=False
    try:
        while len(data)<=limit:
            chunk=os.read(stream.fileno(),min(4096,limit+1-len(data)))
            if not chunk:complete=True;break
            data.extend(chunk)
    except OSError as exc:error=type(exc).__name__+': '+str(exc)
    raw=bytes(data)
    return raw,{'base64':base64.b64encode(raw).decode('ascii'),'bytes':len(raw),
                'sha256':hashlib.sha256(raw).hexdigest(),'complete':complete and len(raw)<=limit,'error':error}

def main():
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={7}:raise ValueError('root CPU7 required')
    if len(sys.argv)!=2:raise ValueError('reader gate token missing')
    token=json.loads(sys.argv[1])
    for signum in STOP_SIGNALS:signal.signal(signum,stop)
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
        command=[PYTHON,'-I','-B','/proc/self/fd/%d'%fd]
        clean_env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','LC_ALL':'C'}
        pre_reader_gate=parent_effect_gate(token)
        proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              start_new_session=True,env=clean_env,pass_fds=(fd,),preexec_fn=child_limits)
    finally:os.close(fd)
    child=None;waited=None;waitstatus=None;error=None;out=b'';err=b'';closed=False;group_absent=False
    stdout_record={'base64':'','bytes':0,'sha256':hashlib.sha256(b'').hexdigest(),'complete':False,'error':'not read'}
    stderr_record=dict(stdout_record)
    try:
        child=proc_identity(proc.pid)
        if child['ppid']!=parent['pid'] or child['pgid']!=child['pid'] or child['sid']!=child['pid']:raise ValueError('reader identity mismatch')
        until=time.monotonic()+10
        while not terminal(proc.pid):
            if stopping or signal.sigpending() & STOP_SIGNALS:raise InterruptedError('stop during reader')
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
            out,stdout_record=bounded_stream(proc.stdout,4096)
            err,stderr_record=bounded_stream(proc.stderr,4096)
            proc.stdout.close();proc.stderr.close();closed=True
            group_absent=not members(proc.pid)
            if not stdout_record['complete'] or not stderr_record['complete']:
                raise ValueError('reader stream incomplete or over bound')
            if err:raise ValueError('reader stderr nonempty')
    except BaseException as exc:error=(error or '')+'; join '+type(exc).__name__+': '+str(exc)
    result={'status':'UNKNOWN_DAEMON_PARENT','pre_reader_gate':pre_reader_gate,'parent':parent,'reader':child,'reader_wait4_pid':waited,
            'reader_wait4_status':waitstatus,'reader_direct_joined':waited==proc.pid,'reader_group_absent':group_absent,
            'reader_streams_closed':closed,'reader_stdout':stdout_record,'reader_stderr':stderr_record,
            'error':error,'current_free':False}
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
