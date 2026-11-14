"""Fixed adaptation of accepted990807 owned_capture for one offline stage.
Root CPU6/source/profile grant is required; no native/root/heavy authority.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent

def exact(row):
    p=Path(row['path']);a=p.lstat();raw=p.read_bytes();b=p.lstat()
    assert stat.S_ISREG(a.st_mode) and len(raw)==row.get('bytes',row.get('size')) and hashlib.sha256(raw).hexdigest()==row['sha256']
    if 'mode'in row:assert a.st_mode==row['mode']
    assert all(getattr(a,k)==getattr(b,k)for k in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns'))
    return raw

def main():
    begin=time.monotonic();data=json.loads((D/'EXECUTION-DATA.json').read_bytes())
    for row in data['private_sources']:exact(row)
    exact(data['capture_engine']);exact(data['census_engine'])
    cfg=json.loads(exact(data['inputs']))
    for row in cfg['refs'].values():exact(row)
    s=importlib.util.spec_from_file_location('accepted_child_stage_owned_capture',data['capture_engine']['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    m.STOP_SIGNALS.add(signal.SIGXCPU)
    for number in m.STOP_SIGNALS:signal.signal(number,m.stop)
    assert resource.getrlimit(resource.RLIMIT_CPU)==(30,30);resource.setrlimit(resource.RLIMIT_CPU,(2,30))
    signal.setitimer(signal.ITIMER_REAL,max(0.1,40-(time.monotonic()-begin)))
    assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000 and os.sched_getaffinity(0)=={6}
    for kind,val in [(resource.RLIMIT_AS,1<<30),(resource.RLIMIT_FSIZE,64<<20),(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256)]:assert resource.getrlimit(kind)==(val,val)
    assert hashlib.sha256(m.CENSUS_SOURCE.read_bytes()).hexdigest()==m.CENSUS_SHA
    assert not os.path.lexists('/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock')
    state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert state['phase']=='running'and not state.get('pause_reason')and not state.get('stop_reason')and state['last_rate_limits']['primary']['usedPercent']<100
    for name in ['stage-attempt-1','actual-stage-capture-1','collector-0755']:assert not os.path.lexists(D/name)
    scratch=Path('/home/holden/mckernel-work/scratch')
    mount=json.loads(subprocess.check_output(['/usr/bin/findmnt','-J','-o','SOURCE,TARGET,UUID,MAJ:MIN','-T',str(scratch)],text=True,timeout=3))['filesystems'][0];dev=scratch.stat().st_dev
    assert mount['uuid']=='2a5768c8-718d-4914-bdc0-6b32c5a92a52'and mount['target']==str(scratch)and mount['maj:min']=='%d:%d'%(os.major(dev),os.minor(dev))
    mem=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024;assert mem>=5<<30
    storage=[]
    for p,floor,growth in [(D,16<<30,512<<20),(scratch,12<<30,0)]:
        v=os.statvfs(p);free=v.f_bavail*v.f_frsize;assert free>=floor+growth;storage.append(dict(path=str(p),free_bytes=free,floor=floor,growth=growth))
    O=D/'actual-stage-capture-1';O.mkdir(mode=0o700)
    m.write(O/'admission.json',dict(command=data['command'],root_external_CPU6_grant_required=True,storage=storage,mem_available_bytes=mem,used_percent=state['last_rate_limits']['primary']['usedPercent'],scratch=mount))
    record=None;failed=None
    try:
        assert 40-(time.monotonic()-begin)>=38,'whole35s child plus retirement headroom'
        def limits():
            for kind,val in [(resource.RLIMIT_CPU,28),(resource.RLIMIT_AS,1<<30),(resource.RLIMIT_FSIZE,64<<20),(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256)]:resource.setrlimit(kind,(val,val))
        record=m.owned_capture(data['command'],O,35,limits)
        m.write(O/'status.json',record)
        if record['returncode']!=0 or not record['direct_child_joined']or not record['group_absent']or record['timed_out']or record['error']or record['retirement_error']:failed='first pipeline failure'
        assert m.cpu_used()<=30,'aggregate30CPU'
    except BaseException as exc:failed=type(exc).__name__+': '+str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        m.write(O/'whole.json',dict(record=record,failure=failed,elapsed_seconds=time.monotonic()-begin,aggregate_CPU_seconds=m.cpu_used(),guest_runs=0,compiler_runs=0,root_operations=0))
    print(json.dumps(dict(status='PASS_OFFLINE_CHILD_STAGE_PIPELINE'if failed is None else 'FAIL',failure=failed,guest_runs=0),sort_keys=True))
    return 0 if failed is None else 1

if __name__=='__main__':raise SystemExit(main())
