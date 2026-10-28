"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Unprivileged build-only container payload. No host/native/cleanup/control operations.
"""
import hashlib,json,os,resource,signal,subprocess,sys,time
from pathlib import Path

def require(ok,message):
    if not ok:raise RuntimeError(message)
def reference(path):
    p=Path(path);h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
    return dict(path=str(p),bytes=p.stat().st_size,sha256=h.hexdigest())
CUTOFFS=[1793253600.0, 1035704.5689393478, 1051042.6959879305]
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
def window_remaining():
    clocks=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'same boot')
    remaining=min(cutoff-now for now,cutoff in zip(clocks,CUTOFFS))
    require(remaining>0,'fixed actual three-clock cutoff')
    return remaining
def alarm_handler(signum,frame):raise TimeoutError('reviewed finite build-only wall/deadline bound')
def execute(plan_path):
    plan=json.loads(Path(plan_path).read_text());out=Path('/work/evidence')
    require(os.getuid()==os.geteuid()==1000,'UID1000 required')
    require(os.sched_getaffinity(0)=={2,3,4,5},'exact reserved CPU2-5')
    require(plan['runtime_authority'] is None,'input plan must not act as runtime authority')
    require(len(plan['commands'])==4,'exact four selected build commands')
    require(plan['deadline_epoch']==1793253600,'fixed actual campaign deadline')
    seconds=min(19800,int(window_remaining()))
    require(seconds>0,'before fixed deadline');signal.signal(signal.SIGALRM,alarm_handler);signal.alarm(seconds)
    for row in plan['tool_files']:
        require(reference(row['path'])==row,'qualified pinned executable/library bytes')
    records=[]
    try:
        for index,command in enumerate(plan['commands']):
            window_remaining()
            target=Path(command['new_output'])
            require(not target.exists() and not target.is_symlink(),'replacement/output must be freshly produced')
            started=time.time();usage=resource.getrusage(resource.RUSAGE_CHILDREN)
            with (out/('%02d.stdout'%index)).open('xb') as stdout,(out/('%02d.stderr'%index)).open('xb') as stderr:
                # No shell, retries, fixture symbols, SDK compiles or old-owner entry.
                child=subprocess.Popen(command['argv'],cwd=command['cwd'],stdout=stdout,stderr=stderr)
                returncode=child.wait()
            after=resource.getrusage(resource.RUSAGE_CHILDREN)
            row=dict(index=index,argv=command['argv'],cwd=command['cwd'],started_at_epoch=started,finished_at_epoch=time.time(),returncode=returncode,CPU_seconds=(after.ru_utime+after.ru_stime)-(usage.ru_utime+usage.ru_stime),maximum_child_RSS_KiB=after.ru_maxrss)
            records.append(row)
            require(returncode==0,'first failed compiler/link stops suffix')
            require(target.is_file() and not target.is_symlink() and target.stat().st_size>0,'new ordinary output required')
            row['output']=reference(target)
        (out/'producer-contract.json').write_text(json.dumps(dict(status='ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER',source_profile=plan['source_profile'],contract=plan['producer_contract'],commands=records,configuration_reuse_not_fresh_configure=True,default_native_retirement_acceptance=False),indent=2)+'\n')
        status='PASS_BUILD_ONLY_PENDING_CURRENT_DEFAULT_AND_NATIVE_VALIDATORS'
    except BaseException as error:
        status='FAIL_PRESERVE_CAPTURE_NO_AUTOMATIC_RETRY'
        (out/'worker-result.json').write_text(json.dumps(dict(status=status,error=repr(error),commands=records),indent=2)+'\n')
        raise
    else:
        (out/'worker-result.json').write_text(json.dumps(dict(status=status,commands=records,default_native_retirement_acceptance=False),indent=2)+'\n')
    finally:signal.alarm(0)

if __name__=='__main__':
    require(len(sys.argv)==2,'one exact plan argument');execute(sys.argv[1])
