"""Once ordinary child normalization/parent capture; wait for root grant."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import resource
import signal
import stat
import time

D=Path(__file__).resolve().parent
PROPOSAL_SHA='7a66d2b115fcb3af037cc472130050f46ae5d43b8908b1b24c1b1ae91473826b'
# Genuine exact review fullref is supplied by root only after it closes.
import sys
assert len(sys.argv)==3, 'usage: oncecaller REVIEW_PATH REVIEW_SHA256'
REVIEW=Path(sys.argv[1])
REVIEW_SHA=sys.argv[2]
ENGINE=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
ENGINE_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'

def write(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(value,stream,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def main():
    begin=time.monotonic()
    assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000 and os.sched_getaffinity(0)=={6}
    raw=(D/'ORDINARY-NORMALIZATION-PARENT-PROPOSAL.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==PROPOSAL_SHA
    assert hashlib.sha256(REVIEW.read_bytes()).hexdigest()==REVIEW_SHA
    assert hashlib.sha256(ENGINE.read_bytes()).hexdigest()==ENGINE_SHA
    proposal=json.loads(raw);O=D/'ordinary-capture-1';assert not os.path.lexists(O) and not os.path.lexists(D/'ACTUAL-CLOSED-HANDOFF.json')
    state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());used=state['last_rate_limits']['primary']['usedPercent'];assert state['phase']=='running' and not state['stop_reason'] and used<100
    mem=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024;assert mem>=5*1024**3
    capacity=[]
    for path,floor,growth in [(D,16*1024**3,64*1024**2),(Path('/home/holden/mckernel-work/scratch'),12*1024**3,1024**2)]:
        v=os.statvfs(path);available=v.f_bavail*v.f_frsize;assert available>=floor+growth;capacity.append(dict(path=str(path),available_bytes=available,floor_bytes=floor,growth_bytes=growth))
    pinref=proposal['source_input_pins'];pinraw=Path(pinref['path']).read_bytes();assert len(pinraw)==pinref['size'] and hashlib.sha256(pinraw).hexdigest()==pinref['sha256']
    inputs=json.loads(pinraw)
    for row in inputs:
        path=Path(row['path']);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            a=os.fstat(fd);assert stat.S_ISREG(a.st_mode)and a.st_size==row['size']and a.st_mode==row['mode'];h=hashlib.sha256()
            while True:
                block=os.read(fd,1<<20)
                if not block:break
                h.update(block)
            assert h.hexdigest()==row['sha256'],row['path']
            b=os.fstat(fd);c=path.lstat();assert all(getattr(a,k)==getattr(b,k)==getattr(c,k)for k in ('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
        finally:os.close(fd)
    inventory=[];collisions=[];uncertain=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            data=(entry/'stat').read_text();fields=data.rsplit(')',1)[1].split();pid=int(entry.name);birth=int(fields[19]);flags=int(fields[6]);affinity=sorted(os.sched_getaffinity(pid));cmd=(entry/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')[:600]
            again=(entry/'stat').read_text().rsplit(')',1)[1].split();assert int(again[19])==birth
            row=dict(pid=pid,start=birth,flags=flags,positive_kernel_thread=bool(flags&0x00200000),affinity=affinity,command=cmd);inventory.append(row)
            if not row['positive_kernel_thread']and affinity==[6]and pid!=os.getpid():
                # This admitted command's ancestors are launcher wrappers only;
                # retain and classify by actual ancestry below, never names.
                collisions.append(row)
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:uncertain.append(int(entry.name))
    ancestors=set();pid=os.getppid()
    while pid>1:
        ancestors.add(pid)
        try:pid=int(Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[1])
        except FileNotFoundError:break
    collisions=[r for r in collisions if r['pid']not in ancestors]
    assert not collisions and not uncertain,(collisions,uncertain)
    for output in proposal['write_allowlist']:
        assert not os.path.lexists(output), 'fresh output '+output
    spec=importlib.util.spec_from_file_location('accepted_ordinary_capture',ENGINE);capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
    O.mkdir(mode=0o700)
    write(O/'admission.json',dict(proposal_sha256=PROPOSAL_SHA,review_sha256=REVIEW_SHA,root_grant='ROOT once ordinary grant exact7a66 normalization/parent required externally before this caller',included_used_percent=used,service_phase=state['phase'],mem_available_bytes=mem,capacity=capacity,source_pins_exact=len(inputs),CPU6_inventory=inventory,CPU6_collisions=collisions,uncertain=uncertain,aggregate_jobs=1,aggregate_planned_bytes=1073741824,other_active_allowance_min_bytes=4*1024**3))
    write(O/'command.json',dict(argv=proposal['argv']))
    for number in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(number,capture.stop)
    signal.setitimer(signal.ITIMER_REAL,35)
    def limits():
        os.sched_setaffinity(0,{6})
        resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824));resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
    try:record=capture.owned_capture(dict(argv=proposal['argv']),O,35,limits)
    finally:signal.setitimer(signal.ITIMER_REAL,0)
    write(O/'status.json',record)
    ok=record['returncode']==0 and record['direct_child_joined']and record['group_absent']and record['closed_streams']and not record['error']and not record['retirement_error']and not record['timed_out']and record['captures']['stderr']['size']==0
    stdout=(O/'stdout').read_text();assert len(stdout.splitlines())<=5 and len(stdout)<10000
    result=dict(status='PASS_CHILD_RAW_NORMALIZATION_PARENT_WHOLE_OWNER_PREFLIGHT'if ok else'FAIL_PRESERVE_FIRST',child=record,elapsed_seconds=time.monotonic()-begin,total_CPU_seconds=capture.cpu_used(),witness_lines=stdout.splitlines(),source_pins_exact=len(inputs),root_operations=0,archive_runs=0,guest_runs=0,normalized_runtime_outputs=1 if ok else None,parent_creations=1 if ok else None,native_acceptance=False,ABI_acceptance=False,final_ACK_acceptance=False)
    assert result['total_CPU_seconds']<=30
    write(O/'whole.json',result)
    print(json.dumps(dict(status=result['status'],returncode=record['returncode'],seconds=result['elapsed_seconds'],cpu=result['total_CPU_seconds'],direct_joined=record['direct_child_joined'],group_absent=record['group_absent'],closed_streams=record['closed_streams'])))
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
