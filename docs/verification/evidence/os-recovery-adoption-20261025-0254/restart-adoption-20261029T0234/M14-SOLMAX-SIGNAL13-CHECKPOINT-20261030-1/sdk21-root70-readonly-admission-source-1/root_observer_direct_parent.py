"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One proposed direct root parent for the exact Root70 read-only observer.
Not an execution release; no result implies current-free or native cleanup.
"""
import hashlib,json,os,resource,signal,stat,subprocess,sys,time
from pathlib import Path

HERE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-root70-readonly-admission-source-1')
OBSERVER=HERE/'read_root70_identity.py';OBSERVER_SHA='b5a1bc9c4b49142cddee82c1df49b356d5d0972f71acda0146f3a34baa6c9f13'
PACKET=HERE/'ROOT70-READONLY-OPERATION.SOURCE-ONLY.json';PACKET_SHA='fca24f38dc603f2b4f04708ec5be890ded7cd22efd7a845850a692797d63e39e'
RELEASE=HERE/'ROOT-OBSERVER-RELEASE.ACTUAL.json';OUTPUT=HERE/'root70-direct-parent-1';INNER=HERE/'root70-observation-1'
CONTROLS=HERE.parent/'ACTUAL-CONTROLS-ARMED.json';CAPACITY=HERE.parent/'ACTUAL-CAPACITY-FALLBACK-ARMED.json'
PYTHON='/home/holden/anaconda3/bin/python3';GATE_FD=197
TIME_UTC=1793774133; TIME_BOOT=1571570.695938624; TIME_MONO=1556232.5688914557
GATE='import os,sys; fd=int(sys.argv[1]); b=os.read(fd,1); os.close(fd); b==b"G" or sys.exit(71); os.execv(sys.executable,[sys.executable,"-I","-B",sys.argv[2]])'
stop_signal=None

def stop(signum,frame):
    global stop_signal
    if stop_signal is None:stop_signal=signum

def digest(path,maximum):
    data=path.read_bytes()
    if len(data)>maximum:raise ValueError('source too large')
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def root_release(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=0 or before.st_mode&0o077 or before.st_nlink!=1 or before.st_size>65536:raise ValueError('root release identity/mode')
        data=os.read(fd,65537);after=os.fstat(fd)
        keys=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        if len(data)!=before.st_size or any(getattr(before,k)!=getattr(after,k) for k in keys):raise ValueError('root release changed')
        return json.loads(data),{'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'device':before.st_dev,'inode':before.st_ino}
    finally:os.close(fd)

def atomic_json(path,value):
    tmp=path.with_name(path.name+'.tmp');data=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.link(tmp,path,follow_symlinks=False)
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(directory);tmp.unlink();os.fsync(directory)
    finally:os.close(directory)

def identity(pid):
    data=Path('/proc',str(pid),'stat').read_text()
    if len(data)>65536:raise ValueError('oversized proc stat')
    fields=data.rsplit(')',1)[1].split()
    return {'pid':pid,'birth':int(fields[19]),'ppid':int(fields[1]),'pgrp':int(fields[2]),'sid':int(fields[3])}

def terminal(pid):return os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None

def same_child(expected):
    try:return identity(expected['pid'])==expected
    except (OSError,ValueError,IndexError):return False

def main():
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={7}:raise ValueError('requires root CPU7 direct parent')
    expected_limits={resource.RLIMIT_AS:(1073741824,2147483648),resource.RLIMIT_CPU:(60,60),resource.RLIMIT_FSIZE:(33554432,33554432),resource.RLIMIT_NOFILE:(256,256),resource.RLIMIT_CORE:(0,0)}
    if any(resource.getrlimit(k)!=v for k,v in expected_limits.items()):raise ValueError('direct parent rlimit mismatch')
    here_stat=HERE.lstat()
    if not stat.S_ISDIR(here_stat.st_mode) or here_stat.st_uid!=1000 or here_stat.st_mode&0o077:raise ValueError('unexpected source parent identity')
    root,release=root_release(RELEASE);parent_source=digest(Path(__file__).resolve(),1<<20);observer=digest(OBSERVER,1<<20);packet=digest(PACKET,2<<20)
    if observer['sha256']!=OBSERVER_SHA or packet['sha256']!=PACKET_SHA:raise ValueError('observer/packet mismatch')
    if root.get('status')!='ROOT_RELEASE_EXACT_OBSERVER_ONLY' or root.get('operation')!='root70-readonly-observer-v1':raise ValueError('release operation mismatch')
    if root.get('parent_sha256')!=parent_source['sha256'] or root.get('observer_sha256')!=OBSERVER_SHA or root.get('packet_sha256')!=PACKET_SHA:raise ValueError('release source mismatch')
    if root.get('paid_fallback') is not False or type(root.get('weekly_used_percent')) not in (int,float) or not 0<=root['weekly_used_percent']<100:raise ValueError('included-only guard')
    if root.get('service_status')!='NO_NEW_REJECTION' or root.get('controls_sha256')!=digest(CONTROLS,1<<20)['sha256'] or root.get('capacity_sha256')!=digest(CAPACITY,1<<20)['sha256']:raise ValueError('current control/service binding')
    now=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic();observed=root.get('weekly_observed_utc')
    if not isinstance(observed,(int,float)) or not 0<=now-observed<=30 or now>=TIME_UTC or boot>=TIME_BOOT or mono>=TIME_MONO:raise ValueError('usage freshness or time ceiling')
    if not isinstance(root.get('expiry_utc'),(int,float)) or not now<root['expiry_utc']<=TIME_UTC:raise ValueError('release expiry')
    nonce=root.get('operation_nonce')
    if not isinstance(nonce,str) or len(nonce)!=32 or any(x not in '0123456789abcdef' for x in nonce) or nonce=='4709c9fae2c743a7acd662e93a663358':raise ValueError('fresh operation nonce')
    if os.path.lexists(OUTPUT) or os.path.lexists(INNER):raise ValueError('fixed output namespace already exists')
    OUTPUT.mkdir(mode=0o700);parent=identity(os.getpid());watchdog=identity(parent['ppid']);caller=identity(watchdog['ppid'])
    # Exact timeout wrapper is root's direct parent. Full root/sudo/caller lineage
    # and source immutability must also be checked by the external released owner.
    if os.path.realpath('/proc/%d/exe'%watchdog['pid'])!=os.path.realpath('/usr/bin/timeout'):raise ValueError('unexpected direct watchdog')
    expected_watchdog=['/usr/bin/timeout','--foreground','--signal=TERM','--kill-after=6s','60s','/usr/bin/prlimit','--as=1073741824:2147483648','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--',PYTHON,'-I','-B',str(Path(__file__).resolve())]
    raw_cmd=Path('/proc/%d/cmdline'%watchdog['pid']).read_bytes()
    if len(raw_cmd)>65536 or raw_cmd.rstrip(b'\0').split(b'\0')!=[x.encode() for x in expected_watchdog] or identity(watchdog['pid'])!=watchdog:raise ValueError('watchdog argv or identity mismatch')
    if os.path.realpath('/proc/%d/exe'%caller['pid'])!=os.path.realpath('/usr/bin/sudo'):raise ValueError('unexpected sudo caller')
    argv=['/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--',PYTHON,'-I','-B','-c',GATE,str(GATE_FD),str(OBSERVER)]
    before=time.monotonic();status={'scope':__doc__.splitlines()[0],'operation':'root70-readonly-observer-v1','parent':parent,'watchdog':watchdog,'caller':caller,'release':release,'nonce':nonce,'observer_source':observer,'packet':packet,'observer_argv':argv,'started_utc':now,'positive_wait4_join':False,'query_custody':'UNKNOWN','current_free':False,'physical_release':False,'signals':[]}
    atomic_json(OUTPUT/'INTENT.ACTUAL.json',status)
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,stop)
    readfd,writefd=os.pipe2(os.O_CLOEXEC)
    if writefd==GATE_FD:raise ValueError('gate fd collision')
    if readfd==GATE_FD:os.set_inheritable(readfd,True)
    else:os.dup2(readfd,GATE_FD,inheritable=True);os.close(readfd)
    child=None;child_id=None;gate_open=False;evidence_error=None;waited=None;waitstatus=None;usage=None
    try:
        with (OUTPUT/'stdout').open('xb') as out,(OUTPUT/'stderr').open('xb') as err:
            previous=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGTERM,signal.SIGINT,signal.SIGALRM})
            try:
                def child_mask():signal.pthread_sigmask(signal.SIG_SETMASK,previous)
                child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,pass_fds=(GATE_FD,),preexec_fn=child_mask)
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous);os.close(GATE_FD)
            try:
                child_id=identity(child.pid)
                if child_id['ppid']!=parent['pid'] or child_id['pgrp']!=child.pid or child_id['sid']!=child.pid:raise ValueError('observer parent/group/session mismatch')
                atomic_json(OUTPUT/'STARTED.ACTUAL.json',{'parent':parent,'watchdog':watchdog,'caller':caller,'child':child_id,'argv':argv,'release':release,'started_utc':time.time()})
                if stop_signal is None:os.write(writefd,b'G');gate_open=True
            except BaseException as exc:evidence_error=type(exc).__name__+': '+str(exc)
            finally:os.close(writefd)
            term_time=None;hard=False
            while not terminal(child.pid):
                elapsed=time.monotonic()-before
                if (stop_signal is not None or elapsed>=60) and term_time is None:
                    term_time=time.monotonic()
                    if child_id is not None and same_child(child_id):
                        try:os.kill(child.pid,signal.SIGTERM);status['signals'].append('TERM_EXACT_UNREAPED_CHILD')
                        except ProcessLookupError:pass
                    else:evidence_error=(evidence_error or '')+'; unmatched observer at TERM'
                if term_time is not None and time.monotonic()-term_time>=4 and not hard:
                    hard=True
                    if child_id is not None and same_child(child_id):
                        try:os.kill(child.pid,signal.SIGKILL);status['signals'].append('KILL_EXACT_UNREAPED_CHILD')
                        except ProcessLookupError:pass
                    else:evidence_error=(evidence_error or '')+'; unmatched observer at KILL'
                if term_time is not None and time.monotonic()-term_time>=5.5:break
                time.sleep(0.05)
            if terminal(child.pid):
                waited,waitstatus,usage=os.wait4(child.pid,0);child.returncode=os.waitstatus_to_exitcode(waitstatus)
    except BaseException as exc:
        evidence_error=(evidence_error or '')+'; parent error '+type(exc).__name__+': '+str(exc)
        # Never guess an identity, kill a process group, or claim direct join.
        # The external root watchdog/caller retains all unresolved ownership.
    finally:
        try:os.close(writefd)
        except OSError:pass
    status.update({'child':child_id,'gate_released':gate_open,'observer_returncode':child.returncode if child else None,'wait4_pid':waited,'wait4_status':waitstatus,'positive_wait4_join':child is not None and waited==child.pid,'hard_kill_does_not_prove_query_cleanup':True,'stop_signal':stop_signal,'evidence_error':evidence_error,'finished_utc':time.time(),'wall_seconds':time.monotonic()-before,'user_cpu_seconds':usage.ru_utime if usage else None,'system_cpu_seconds':usage.ru_stime if usage else None,'peak_rss_kib':usage.ru_maxrss if usage else None})
    try:
        status['parent_after']=identity(parent['pid']);status['watchdog_after']=identity(watchdog['pid']);status['caller_after']=identity(caller['pid'])
        if status['parent_after']!=parent or status['watchdog_after']!=watchdog or status['caller_after']!=caller:status['evidence_error']=(status['evidence_error'] or '')+'; parent lineage drift'
    except BaseException as exc:status['evidence_error']=(status['evidence_error'] or '')+'; parent lineage unknown: '+repr(exc)
    try:
        after=HERE.lstat()
        if (after.st_dev,after.st_ino)!=(here_stat.st_dev,here_stat.st_ino):status['evidence_error']=(status['evidence_error'] or '')+'; source directory drift'
    except OSError as exc:status['evidence_error']=(status['evidence_error'] or '')+'; source directory unknown: '+repr(exc)
    try:
        status['stdout']=digest(OUTPUT/'stdout',32<<20);status['stderr']=digest(OUTPUT/'stderr',32<<20);status['streams_closed']=True
    except BaseException as exc:status['streams_closed']=False;status['evidence_error']=(status['evidence_error'] or '')+'; streams unknown: '+repr(exc)
    if status['positive_wait4_join'] and child.returncode==0 and not status['signals'] and not stop_signal and not status['evidence_error']:
        try:
            summary=json.loads((INNER/'summary.json').read_text())
            obs=summary['before'];expected_observer={'pid':child_id['pid'],'start':child_id['birth'],'ppid':parent['pid'],'parent_start':parent['birth'],'pgid':child_id['pgrp'],'sid':child_id['sid']}
            matching_observer=all(obs.get(k)==v for k,v in expected_observer.items())
            if matching_observer and summary['status']=='OBSERVED_BOUNDED_FACTS_NONINTERFERENCE_NOT_ESTABLISHED' and len(summary['events'])==3 and all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] and not x['join']['error'] and not x['join']['retirement_error'] for x in summary['events']):
                status['query_custody']='DIRECT_QUERY_JOINS_RECORDED_DESCENDANT_ESCAPE_UNPROVEN'
            else:status['query_custody']='UNKNOWN_OBSERVER_SUMMARY'
        except BaseException as exc:status['query_custody']='UNKNOWN_SUMMARY: '+repr(exc)
    atomic_json(OUTPUT/'DIRECT-PARENT-JOIN.ACTUAL.json',status)
    print(json.dumps({'positive_wait4_join':status['positive_wait4_join'],'query_custody':status['query_custody'],'current_free':False,'physical_release':False},sort_keys=True))
    return 0 if status['positive_wait4_join'] and child.returncode==0 and not status['evidence_error'] and not status['signals'] and not stop_signal and status['query_custody']=='DIRECT_QUERY_JOINS_RECORDED_DESCENDANT_ESCAPE_UNPROVEN' else 2

if __name__=='__main__':
    try:result=main()
    except BaseException as exc:
        print(json.dumps({'status':'UNKNOWN_PARENT_EARLY_FAILURE','error':type(exc).__name__+': '+str(exc),'current_free':False,'physical_release':False},sort_keys=True),file=sys.stderr);sys.exit(2)
    sys.exit(result)
