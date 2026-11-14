"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Privileged source/request-bound one-command HOST capture. Root owns TERM/anchor/wait; never KILL.
NOT RELEASED. An unretired owner/lease remains live and capture waiting stays active.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, signal, stat, subprocess, sys, time
D=Path(__file__).resolve().parent
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
CAP=384*2**20

OWNER_PATH = '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/failure-dfbb-docker-start-1/runtime-successor-1/source/native_diagnostic_container_owner.py'
RELEASE_PATH = '/home/holden/mckernel-work/scratch/p12s6l1/r.json'
HOST_PARENT = '/home/holden/mckernel-work/native-runs/l12d1/p'
NONCE = '5603c55a294240fdb86c3613ec42e293'
MANIFEST_PATH = '/home/holden/mckernel-work/scratch/p12s6l1/m.json'
MANIFEST_SHA = '2f4c5c6dab2dcc5993df805da4d4c57c1e8d39c7ac2b4118b59ad578cd9c5c57'
LONG_PREFIX=['/usr/bin/prlimit', '--as=2147483648:2147483648', '--cpu=unlimited:unlimited', '--fsize=402653184:402653184', '--core=0:0', '--nofile=4096:4096', '--', '/home/holden/anaconda3/bin/python3', '-I', '-B']

def need(ok,msg):
    if not ok:raise RuntimeError(msg)

def filepin(path,cap):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=cap,'bounded regular single-link input')
        h=hashlib.sha256();n=0
        while True:
            raw=os.read(fd,1048576)
            if not raw:break
            n+=len(raw);need(n<=cap,'input grew past cap');h.update(raw)
        after=os.fstat(fd);named=os.lstat(path)
        fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_nlink')
        need(n==before.st_size and all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields),'stable file identity')
        return dict(path=str(path),size=n,sha256=h.hexdigest())
    finally:os.close(fd)

def main():
    need(len(sys.argv)==3,'request path and exact digest')
    req=Path(sys.argv[1]);need(req.is_absolute() and req.resolve()==req,'canonical request path')
    need(filepin(req,65536)['sha256']==sys.argv[2],'exact request digest')
    r=json.loads(req.read_bytes())
    need(r['schema']=='mckernel.p12.owner-aware-host-capture.v1','capture schema')
    need(filepin(Path(__file__).resolve(),65536)['sha256']==r['wrapper_sha256'],'wrapper source')
    need(filepin(HELPER,65536)['sha256']==HELPER_SHA,'accepted identity helper')
    spec=importlib.util.spec_from_file_location('accepted_capture_facts',HELPER)
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    need(os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7},'root CPU7 capture controller owns signal authority')
    need(resource.getrlimit(resource.RLIMIT_FSIZE)==(CAP,CAP),'parent384MiB hard FSIZE')
    need(resource.getrlimit(resource.RLIMIT_CPU)==(resource.RLIM_INFINITY,resource.RLIM_INFINITY),'parent unlimited CPU retirement profile')
    need(r['stream_file_bytes']==CAP and r['stream_slots']==2 and r['command_count']==r['retained_copies']==1,'exact capture allowance')
    source=Path(r['command_source']['path'])
    need(filepin(source,2**20)['sha256']==r['command_source']['sha256'],'command source')
    argv=r['argv']
    need(r['soft_wall_seconds']==8100,'exact accepted LONG outer softwall')
    need(str(source)==OWNER_PATH and r['long_profile_release']['path']==RELEASE_PATH,'exact LONG owner/release paths')
    need(argv[:3]==['/usr/bin/taskset','-c','7'] and
         argv[3:]==LONG_PREFIX+[str(source),'--owner-sha256',r['command_source']['sha256'],
         '--attempt-parent',HOST_PARENT,'--nonce',NONCE,'--manifest',MANIFEST_PATH,
         '--manifest-sha256',MANIFEST_SHA,'--long-profile-release',RELEASE_PATH,
         '--long-profile-release-sha256',r['long_profile_release']['sha256']],'exact LONG root owner argv')
    out=Path(r['capture_directory']);need(out.parent==req.parent and out.name=='actual-capture-1','exact fresh capture path')
    out.mkdir(mode=0o700);h.write(out/'command.json',r)
    files=[];p=None;term_sent=False;stopped=[False];old={}
    def stop(n,f):stopped[0]=True
    for n in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):old[n]=signal.signal(n,stop)
    begin=time.monotonic();signal_errors=[];rc=None;direct=False;unexpected=[]
    try:
        for name in ('stdout','stderr'):
            fd=os.open(out/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
            files.append(os.fdopen(fd,'wb',buffering=0))
        # Block handled stops until Popen ownership is assigned; restore mask in child.
        previous=signal.pthread_sigmask(signal.SIG_BLOCK,set(old))
        try:
            def unmask():signal.pthread_sigmask(signal.SIG_SETMASK,previous)
            p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=files[0],stderr=files[1],start_new_session=True,preexec_fn=unmask)
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
        birth=h.process_start(p.pid);h.write(out/'started.json',dict(pid=p.pid,start=birth))
        while not h.wait_terminal(p,0.1):
            if (stopped[0] or time.monotonic()-begin>=r['soft_wall_seconds']) and not term_sent:
                # p remains unreaped: its process group number cannot be reused.
                term_sent=True
                try:os.killpg(p.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                except OSError as exc:signal_errors.append(type(exc).__name__)
                h.write(out/'termination-request.json',dict(pid=p.pid,start=birth,signal='TERM',force_kill=False,
                    disposition='Wait for actual owner cleanup/recovery; retain live lease on uncertainty.'))
        # Before direct wait, creator remains an unreaped identity anchor.
        group=h.members(p.pid);unexpected=[pid for pid in group if pid!=p.pid]
        rc=p.wait();direct=True
    finally:
        # All signal errors are retained; none may skip direct wait or closing FDs.
        # Root controller and directly-created root owner share signal authority.
        try:
            if p is not None and p.returncode is None:
                if not term_sent:
                    term_sent=True
                    try:os.killpg(p.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    except OSError as exc:signal_errors.append(type(exc).__name__)
                # Never return while child is unjoined, even if signal failed.
                rc=p.wait();direct=True
        finally:
            for f in files:f.close()
            for n,handler in old.items():signal.signal(n,handler)
    remaining=h.members(p.pid)
    result=dict(returncode=rc,direct_child_joined=direct,closed_streams=True,group_absent=not remaining,
                unexpected_group_members=unexpected,remaining_group_members=remaining,term_sent=term_sent,
                force_kill=False,signal_errors=signal_errors,seconds=time.monotonic()-begin,captures={n:filepin(out/n,CAP) for n in ('stdout','stderr')})
    h.write(out/'CAPTURE-RESULT.json',result)
    need(rc==0 and not term_sent and not signal_errors and not unexpected and not remaining,'capture command or retirement failed')
    print(json.dumps(dict(status='PASS_LONG_NONE_OWNER_CAPTURE_RETIREMENT',capture_result=result,application_acceptance=False)))
if __name__=='__main__':main()
