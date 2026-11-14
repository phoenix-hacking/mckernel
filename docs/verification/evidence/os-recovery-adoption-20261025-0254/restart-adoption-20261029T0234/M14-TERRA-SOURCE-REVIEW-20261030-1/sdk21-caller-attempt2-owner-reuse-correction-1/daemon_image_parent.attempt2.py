#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root direct parent for fixed daemon metadata and one exact SDK image inspect.
"""
import ast,base64,errno,fcntl,hashlib,json,math,os,resource,select,signal,stat,subprocess,sys,time
from pathlib import Path

READER=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-daemon-image-readonly-source-1/daemon_metadata_reader.py')
READER_SHA='b76fd4541fb6c331aaa4022d930149c42ee54e887f080096adab8a43fa202787'
CENSUS=Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-sdk-20261019-1/capsule/scripts/native_rust_exact_build_container_owner.py')
CENSUS_SHA='96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1'
PYTHON='/home/holden/anaconda3/bin/python3.9'
IMAGE='sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'
FORMAT='{{json .Id}}\n{{json .Architecture}}\n{{json .Os}}\n{{json .Config.User}}\n{{json .Config.WorkingDir}}\n{{json (index .Config.Labels "org.opencontainers.image.version")}}\n{{json (index .Config.Labels "mckernel.toolchain")}}'
IMAGE_ARGV=['/usr/bin/docker','--host=unix:///var/run/docker.sock','image','inspect','--format',FORMAT,IMAGE]
DOCKER_SHA='2e94ad2db8c6c9cfffd02d403eea69a2d0bd14c84eb9dccdcebbcf2a68fcc257'

ROOT=Path(__file__).resolve().parent
RELEASE=ROOT/'ROOT-DAEMON-IMAGE-ATTEMPT2-RELEASE.ACTUAL.json'
CONTROLS=ROOT.parent/'ACTUAL-CONTROLS-ARMED.json'
GATE_SOURCE=ROOT/'attempt2_gate.v2.py'
GATE_SHA='dd4a8d449841510f8cf527aec926fe32b974ccc9f2586a335cf792a3ca78f594'
CUSTODY_SOURCE=ROOT/'custody_protocol.py'
CUSTODY_SHA='b86da7810a1981e8d50a822854dcf71134b7e83b3f6a6193df7305b31e9420ba'
CUSTODY_EVENT_FD=3
CUSTODY_ACK_FD=4
UTC_LIMIT=1793774133
BOOT_LIMIT=1571568.6959155537
MONO_LIMIT=1556230.5688700147
BOOT_ID='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
STOP_SIGNALS={signal.SIGTERM,signal.SIGINT,signal.SIGALRM}
stopping=False
OPERATION_DEADLINE=None

def stop(signum,frame):
    global stopping
    stopping=True


def root_file_mode(uid,gid,mode,euid):
    return uid==0 and gid==1000 and mode==0o640

def no_access_acl(fd):
    try:os.getxattr(fd,'system.posix_acl_access')
    except OSError as exc:
        if exc.errno in (errno.ENODATA,errno.ENOTSUP):return
        raise
    raise ValueError('root document extended access ACL not allowed')

def bound_document(path,expected,root=False):
    if not isinstance(expected,list) or len(expected)!=10:raise ValueError('sealed identity token malformed')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        a=os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or a.st_nlink!=1 or a.st_size>2**20:
            raise ValueError('sealed document identity mismatch')
        if root:
            if not root_file_mode(a.st_uid,a.st_gid,stat.S_IMODE(a.st_mode),os.geteuid()):raise ValueError('root document UID/GID/mode differs')
            no_access_acl(fd)
        chunks=[];size=0
        while True:
            z=os.read(fd,65536)
            if not z:break
            size+=len(z)
            if size>2**20:raise ValueError('sealed document growth')
            chunks.append(z)
        c=os.fstat(fd);named=os.lstat(path);keys=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        if size!=a.st_size or any(getattr(a,k)!=getattr(c,k) or getattr(a,k)!=getattr(named,k) for k in keys):raise ValueError('sealed document changed')
        raw=b''.join(chunks);actual=[a.st_dev,a.st_ino,a.st_mode,a.st_uid,a.st_gid,a.st_nlink,a.st_size,a.st_mtime_ns,a.st_ctime_ns,hashlib.sha256(raw).hexdigest()]
        if actual!=expected:raise ValueError('sealed document bytes/identity drift')
        return json.loads(raw)
    finally:os.close(fd)

def validated_overall_deadline(release):
    deadline=release.get('operation_deadline_monotonic')
    now=time.monotonic()
    if type(deadline) not in (int,float) or not math.isfinite(deadline) or not 0<now<deadline<=MONO_LIMIT:
        raise ValueError('invalid absolute overall operation deadline')
    return deadline


def parent_effect_gate(token):
    if stopping or signal.sigpending() & STOP_SIGNALS:raise InterruptedError('stop before reader spawn')
    if not isinstance(token,dict) or set(token)!={'release','controls','nonce'}:
        raise ValueError('reader authority token malformed')
    release=bound_document(RELEASE,token['release'],root=True)
    controls=bound_document(CONTROLS,token['controls'])
    if validated_overall_deadline(release)!=OPERATION_DEADLINE:
        raise ValueError('overall deadline changed')
    if release.get('schema')!='mckernel.sdk13.daemon-image-readonly-release.attempt2.v1' or release.get('operation')!='ONE_DAEMON_METADATA_AND_ONE_EXACT_IMAGE_INSPECT' or release.get('reader_sha256')!=READER_SHA or release.get('image_argv')!=IMAGE_ARGV or release.get('parent_as_bytes')!=536870912 or release.get('image_as_bytes')!=536870912 or release.get('daemon_sample')!='IN_PROCESS' or release.get('image_process_group')!='INHERIT_PARENT_GROUP' or release.get('cpu')!=7 or release.get('query_count')!=1 or release.get('nonce')!=token.get('nonce'):
        raise ValueError('read-only operation release binding differs')
    nonce=token['nonce']
    if not isinstance(nonce,str) or len(nonce)!=32 or any(c not in '0123456789abcdef' for c in nonce):raise ValueError('invalid fresh nonce')
    if release.get('parent_sha256')!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest():raise ValueError('parent source hash differs')
    if release.get('docker_sha256')!=DOCKER_SHA or release.get('gate_sha256')!=GATE_SHA or release.get('custody_sha256')!=CUSTODY_SHA:raise ValueError('tool or protocol source seal differs')
    sup=release.get('capacity_supervisor')
    rows=controls.get('binding')
    if not isinstance(rows,dict) or not isinstance(sup,dict):raise ValueError('missing controller binding')
    # Supervisor must come from a separately authenticated fresh release.
    declared=release.get('controller_identities')
    expected={role:{'pid':row.get('pid'),'ppid':row.get('ppid'),'start':row.get('start')} for role,row in rows.items() if isinstance(row,dict)}
    expected['supervisor']=sup
    if declared!=expected:raise ValueError('sealed controllers differ')
    observed={}
    for role,row in expected.items():
        if not isinstance(row,dict) or type(row.get('pid')) is not int:raise ValueError('controller row malformed')
        raw=Path('/proc/%d/stat'%row['pid']).read_text().rsplit(')',1)[1].split()
        observed[role]={'pid':row['pid'],'ppid':int(raw[1]),'start':raw[19],'state':raw[0]}
    env={'__name__':'attempt2_gate'}
    exec(compile(verified_source(GATE_SOURCE,GATE_SHA),str(GATE_SOURCE),'exec'),env)
    stopped=any(os.path.lexists(CONTROLS.parent/name) for name in ('HOLD','USER-STOP','STOP','HOLD.json','USER-STOP.json'))
    env['check_controls'](controls,sup,observed,time.time(),time.clock_gettime(time.CLOCK_BOOTTIME),time.monotonic(),Path('/proc/sys/kernel/random/boot_id').read_text().strip(),stopped)
    # Deliberate source-only hold: proc liveness is not guardian/monitor health.
    # An independently reviewed fresh authenticated health contract is required.
    raise ValueError('current controller health is not bound; source-only hold')
    facts=release.get('admission')
    if not isinstance(facts,dict) or facts.get('service_status')!='NO_NEW_REJECTION' or facts.get('paid_fallback') is not False or facts.get('reader_compiler_overlap') is not False or facts.get('native_reserve_bytes')!=12884901888 or facts.get('v2_unknown_reserved_bytes')!=2147483648:
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

def image_tool_binding():
    # A recorded binary digest is not a claim about image-internal tool bytes.
    path=Path(IMAGE_ARGV[0]);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd);h=hashlib.sha256();count=0
        if not stat.S_ISREG(before.st_mode) or before.st_size>128*1024*1024:raise ValueError('Docker client type/size')
        while True:
            block=os.read(fd,1048576)
            if not block:break
            h.update(block);count+=len(block)
        after=os.fstat(fd);named=os.lstat(path)
        keys=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')
        if count!=before.st_size or any(getattr(before,k)!=getattr(after,k) or getattr(after,k)!=getattr(named,k) for k in keys) or h.hexdigest()!=DOCKER_SHA:raise ValueError('Docker client binding changed')
    finally:os.close(fd)


OPERATION_DIR=None

def claim_fresh_nonce(token):
    global OPERATION_DIR
    parent_effect_gate(token)
    release=bound_document(RELEASE,token['release'],root=True)
    output=Path(release.get('output_parent',''))
    if not output.is_absolute() or str(output)!=os.path.normpath(str(output)) or output.resolve(strict=True)!=output:raise ValueError('output parent path invalid')
    st=os.lstat(output)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022 or release.get('output_parent_identity')!=[st.st_dev,st.st_ino,st.st_uid,st.st_gid,st.st_mode]:raise ValueError('output parent identity differs')
    path=output/('daemon-image-readonly-'+token['nonce'])
    os.mkdir(path,0o700)  # Exclusive, permanent consumed nonce marker; never removed here.
    marker=path/'nonce-claimed.json'
    with marker.open('x') as f:
        json.dump({'nonce':token['nonce'],'operation':'ONE_DAEMON_METADATA_AND_ONE_EXACT_IMAGE_INSPECT','current_free':False},f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    for directory in (path,output):
        fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        try:os.fsync(fd)
        finally:os.close(fd)
    OPERATION_DIR=path


def require_private_group(parent,baseline):
    keys={'pid','birth','ppid','pgid','sid'}
    if (not isinstance(parent,dict) or set(parent)!=keys or
        any(type(parent[k]) is not int or parent[k]<=0 for k in keys) or
        parent['pgid']!=parent['pid'] or baseline!={}):
        raise ValueError('parent must own a private group with empty outer baseline')


def group_baseline(token,parent):
    """Only the parent may occupy its private group before the image child."""
    require_private_group(parent,{})
    release=bound_document(RELEASE,token['release'],root=True)
    if (type(release.get('parent_pgid')) is not int or type(release.get('parent_sid')) is not int or
        release.get('parent_pgid')!=parent['pid'] or release.get('parent_sid')!=parent['sid'] or
        release.get('outer_group_identities')!=[]):
        raise ValueError('release must bind the private parent group and empty outer list')
    if proc_identity(parent['pid'])!=parent:raise ValueError('parent identity changed')
    if members(parent['pgid'])!=[parent['pid']]:raise ValueError('private group has unexpected member')
    return {}


def release_held_gate(token,parent,child,baseline,gate_fd,deadline):
    require_private_group(parent,baseline)
    keys={'pid','birth','ppid','pgid','sid'}
    if (not isinstance(child,dict) or set(child)!=keys or
        any(type(child[k]) is not int or child[k]<=0 for k in keys) or child['pid']==parent['pid']):
        raise ValueError('image child identity malformed')
    if stopping or signal.sigpending() & STOP_SIGNALS:raise InterruptedError('stop before GO validation')
    gate=parent_custody_gate(token)
    if gate is not True:raise ValueError('parent gate did not explicitly pass')
    if proc_identity(parent['pid'])!=parent or proc_identity(child['pid'])!=child:raise ValueError('parent/child identity changed before GO')
    if child['ppid']!=parent['pid'] or child['pgid']!=parent['pgid'] or child['sid']!=parent['sid']:raise ValueError('child not in owned parent group')
    for pid,item in baseline.items():
        if proc_identity(pid)!=item:raise ValueError('outer member identity changed before GO')
    expected=sorted([parent['pid'],child['pid'],*baseline])
    if members(parent['pgid'])!=expected:raise ValueError('owned group has missing or unexpected actor')
    if stopping or signal.sigpending() & STOP_SIGNALS:raise InterruptedError('stop before GO')
    if time.monotonic()>=deadline:raise TimeoutError('held child deadline expired before GO')
    if os.write(gate_fd,b'G')!=1:raise OSError('short GO write')
    return gate


def inspect_image_once(token,parent,baseline):
    # Whole-operation outer owned watchdog remains mandatory for blocked fork,
    # wait, fsync or proc access. The child inherits this already-owned group.
    pre=parent_effect_gate(token)
    if group_baseline(token,parent)!=baseline:raise ValueError('outer group drift before image')
    if OPERATION_DIR is None:raise ValueError('nonce was not claimed')
    path=OPERATION_DIR;image_tool_binding()
    outfd=os.open(path/'image.stdout',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:errfd=os.open(path/'image.stderr',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    except BaseException:os.close(outfd);raise
    ready_r,ready_w=os.pipe2(os.O_CLOEXEC);gate_r,gate_w=os.pipe2(os.O_CLOEXEC)
    pid=None;child=None;waited=None;code=None;usage=None;error=None;members_before=None;gate=None;released=False
    immutable_argv=tuple(IMAGE_ARGV);deadline=OPERATION_DEADLINE
    try:
        previous=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
        try:
            pid=os.fork()
            if pid==0:
                try:
                    os.close(ready_r);os.close(gate_w);os.close(CUSTODY_EVENT_FD);os.close(CUSTODY_ACK_FD);os.dup2(outfd,1);os.dup2(errfd,2)
                    child_limits();signal.pthread_sigmask(signal.SIG_SETMASK,previous)
                    if os.write(ready_w,b'R')!=1:os._exit(121)
                    os.close(ready_w)
                    if os.read(gate_r,1)!=b'G':os._exit(121)
                    os.close(gate_r)
                    os.execve(immutable_argv[0],immutable_argv,{'PATH':'/usr/bin:/bin','HOME':'/nonexistent','LANG':'C','LC_ALL':'C'})
                except BaseException:os._exit(122)
        finally:
            if pid!=0:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
        os.close(ready_w);ready_w=-1;os.close(gate_r);gate_r=-1
        while True:
            if stopping or signal.sigpending() & STOP_SIGNALS:raise InterruptedError('stop before READY')
            if time.monotonic()>=deadline:raise TimeoutError('image READY timeout')
            readable,_,_=select.select([ready_r],[],[],min(.05,max(0,deadline-time.monotonic())))
            if readable:
                if os.read(ready_r,1)!=b'R':raise ValueError('image child exited without READY')
                break
        child=proc_identity(pid)
        if child['ppid']!=parent['pid'] or child['pgid']!=parent['pgid'] or child['sid']!=parent['sid']:raise ValueError('child inherited unexpected group/session')
        with (path/'image-started.json').open('x') as f:
            json.dump({'parent':parent,'client':child,'argv':list(immutable_argv),'gate_released':False},f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
        dfd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        try:os.fsync(dfd)
        finally:os.close(dfd)
        custody_ack(token,'IMAGE_READY',parent,child,deadline)
        gate=release_held_gate(token,parent,child,baseline,gate_w,deadline);released=True
        os.close(gate_w);gate_w=-1
        while not terminal(pid):
            if stopping or signal.sigpending() & STOP_SIGNALS:raise InterruptedError('stop during image inspect')
            if time.monotonic()>=deadline:raise TimeoutError('image inspect timeout')
            time.sleep(.01)
        members_before=members(parent['pgid'])
        if members_before!=sorted([parent['pid'],pid,*baseline]):raise ValueError('owned group changed before child wait4')
    except BaseException as exc:
        error=type(exc).__name__+': '+str(exc)
        if gate_w>=0:os.close(gate_w);gate_w=-1
        if pid is not None and child is not None:
            try:
                # The group includes our owner. Never killpg here; signal only
                # this same unreaped, positively identified direct child.
                if proc_identity(pid)==child:
                    os.kill(pid,signal.SIGTERM);until=min(OPERATION_DEADLINE,time.monotonic()+1)
                    while not terminal(pid) and time.monotonic()<until:time.sleep(.01)
                    if not terminal(pid) and proc_identity(pid)==child:os.kill(pid,signal.SIGKILL)
            except (OSError,ValueError,IndexError):pass
    finally:
        for fd in (ready_r,ready_w,gate_r,gate_w):
            if fd>=0:
                try:os.close(fd)
                except OSError:pass
        if pid is not None:
            try:
                until=min(OPERATION_DEADLINE,time.monotonic()+2)
                while not terminal(pid) and time.monotonic()<until:time.sleep(.01)
                if terminal(pid):waited,status,usage=os.wait4(pid,0);code=os.waitstatus_to_exitcode(status)
            except BaseException as exc:error=(error or '')+'; wait4 '+repr(exc)
        os.fsync(outfd);os.fsync(errfd);os.close(outfd);os.close(errfd)
    raw=(path/'image.stdout').read_bytes();err=(path/'image.stderr').read_bytes()
    result={'path':str(path),'argv':list(immutable_argv),'pre_image_gate':pre,'pre_go':gate,'client':child,'gate_released':released,'wait4_pid':waited,'exit_code':code,'group_before_child_reap':members_before,'outer_group_absence':'NOT_CLAIMED_PARENT_STILL_LIVE','stdout_sha256':hashlib.sha256(raw).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest(),'stdout_bytes':len(raw),'stderr_bytes':len(err),'overall_deadline_monotonic':OPERATION_DEADLINE,'user_seconds':usage.ru_utime if usage else None,'system_seconds':usage.ru_stime if usage else None,'max_rss_kib':usage.ru_maxrss if usage else None,'error':error}
    record=path/'image-result.json'
    with record.open('x') as f:json.dump(result,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    if error or not released or child is None or waited!=pid or code!=0 or members_before!=sorted([parent['pid'],pid,*baseline]) or len(raw)>4096 or err:raise ValueError('image client outcome not established; see '+str(record))
    fields=[json.loads(line) for line in raw.splitlines()]
    if len(fields)!=7 or fields[:3]!=[IMAGE,'amd64','linux']:raise ValueError('image inspect identity/architecture differs; see '+str(record))
    result.update(observed={'id':fields[0],'architecture':fields[1],'os':fields[2],'user':fields[3],'working_dir':fields[4],'image_version_label':fields[5],'toolchain_label':fields[6]},toolchain_bytes_verified=False)
    return result


def parent_custody_gate(token):
    result=parent_effect_gate(token)
    keys={'utc','boot','mono','weekly_observed_utc','expiry_utc'}
    if not isinstance(result,dict) or set(result)!=keys:
        raise ValueError('parent admission gate did not explicitly pass')
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in result.values()):
        raise ValueError('parent admission gate result invalid')
    if not (result['utc']<result['expiry_utc']<=UTC_LIMIT and
            0<=result['utc']-result['weekly_observed_utc']<=30 and
            result['boot']<BOOT_LIMIT and result['mono']<MONO_LIMIT):
        raise ValueError('parent admission gate result expired')
    return True


def custody_ack(token,phase,parent,child,deadline):
    raw=verified_source(CUSTODY_SOURCE,CUSTODY_SHA)
    env={'__name__':'custody_protocol'}
    exec(compile(raw,str(CUSTODY_SOURCE),'exec'),env)
    env['parent_handshake'](CUSTODY_EVENT_FD,CUSTODY_ACK_FD,token['nonce'],phase,
                            parent,child,deadline,
                            lambda:parent_custody_gate(token),
                            lambda:stopping or bool(signal.sigpending() & STOP_SIGNALS))


def sample_daemon_in_process(token,parent,baseline):
    before=parent_effect_gate(token)
    if group_baseline(token,parent)!=baseline:raise ValueError('outer group drift before sample')
    raw=verified_source(READER,READER_SHA)
    module={'__name__':'sdk13_readonly_inprocess_reader'};exec(compile(raw,str(READER),'exec'),module)
    sample=json.loads(module['sample']())
    if sample.get('status')!='OBSERVED_EXACT_DAEMON_READONLY' or sample.get('reader')!=parent:raise ValueError('in-process sample parent identity differs')
    after=parent_effect_gate(token)
    if group_baseline(token,parent)!=baseline:raise ValueError('outer group drift during sample')
    record={'status':'OBSERVED_DAEMON_IN_ROOT_PARENT','parent':parent,'daemon_sample':sample,'before_gate':before,'after_gate':after,'current_free':False}
    with (OPERATION_DIR/'daemon-sample.json').open('x') as f:json.dump(record,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    return record


def main():
    global OPERATION_DEADLINE
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={7}:raise ValueError('root CPU7 required')
    for kind,value in ((resource.RLIMIT_AS,536870912),(resource.RLIMIT_CPU,20),
                       (resource.RLIMIT_NOFILE,128),(resource.RLIMIT_FSIZE,1048576),
                       (resource.RLIMIT_CORE,0)):
        if resource.getrlimit(kind)!=(value,value):raise ValueError('root parent limits differ')
    if len(sys.argv)!=2:raise ValueError('gate token missing')
    token=json.loads(sys.argv[1])
    OPERATION_DEADLINE=validated_overall_deadline(bound_document(RELEASE,token['release'],root=True))
    for signum in STOP_SIGNALS:signal.signal(signum,stop)
    parent=proc_identity(os.getpid());baseline=group_baseline(token,parent)
    claim_fresh_nonce(token)
    with (OPERATION_DIR/'parent-started.json').open('x') as f:
        json.dump({'parent':parent,'scope':'OWNED_PARENT_IDENTITY_ONLY','current_free':False},f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    parent_dir_fd=os.open(OPERATION_DIR,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(parent_dir_fd)
    finally:os.close(parent_dir_fd)
    custody_ack(token,'PARENT_READY',parent,None,OPERATION_DEADLINE)
    result={'status':'UNKNOWN_DAEMON_IMAGE_PARENT','parent':parent,'outer_group_absence':'NOT_CLAIMED_PARENT_STILL_LIVE','current_free':False,'toolchain_bytes_verified':False}
    try:
        result['daemon']=sample_daemon_in_process(token,parent,baseline)
        result['image']=inspect_image_once(token,parent,baseline)
        result['status']='OBSERVED_DAEMON_AND_IMAGE_NO_ADMISSION'
    except BaseException as exc:result['error']=type(exc).__name__+': '+str(exc)
    own_usage=resource.getrusage(resource.RUSAGE_SELF)
    result['parent_resource']={'user_seconds':own_usage.ru_utime,'system_seconds':own_usage.ru_stime,'max_rss_kib':own_usage.ru_maxrss}
    print(json.dumps(result,sort_keys=True),flush=True)
    return 0 if result['status']=='OBSERVED_DAEMON_AND_IMAGE_NO_ADMISSION' else 2

if __name__=='__main__':
    try:code=main()
    except BaseException as exc:
        print(json.dumps({'status':'UNKNOWN_DAEMON_PARENT','error':type(exc).__name__+': '+str(exc),
                          'current_free':False},sort_keys=True),flush=True);sys.exit(2)
    sys.exit(code)
