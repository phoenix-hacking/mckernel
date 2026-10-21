"""The same finite settid fixture, using the pinned existing owned-capture API."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,sys,time

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent
OUT=HERE/'check-1'
HELPER=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
RUSTC='/home/holden/mckernel-work/scratch/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/bin/rustc'
CC='/usr/bin/x86_64-linux-gnu-gcc-9'
COMMON=[CC,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fno-lto','-I',str(SOURCE/'fixture-1')]
COMMANDS=[
 ('rust-object',[RUSTC,'--edition=2021','--crate-name','actual_settid_helper','--crate-type=lib','--emit=obj','-Dwarnings','-Cpanic=abort','-Copt-level=2','-Ccodegen-units=1','-Zthreads=1',str(SOURCE/'fixture-1/actual-helper.rs'),'-o',str(OUT/'actual-helper.o')]),
 ('original-c',COMMON+['-c',str(SOURCE/'fixture-1/original.c'),'-o',str(OUT/'original.o')]),
 ('candidate-c',COMMON+['-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS','-c',str(SOURCE/'fixture-1/candidate.c'),'-o',str(OUT/'candidate.o')]),
 ('link',COMMON+['-no-pie',str(SOURCE/'fixture-1/check.c'),str(OUT/'original.o'),str(OUT/'candidate.o'),str(OUT/'actual-helper.o'),'-Wl,--wrap=syscall_settid_body_result','-o',str(OUT/'actual-settid')]),
 ('actual-12-cases',[str(OUT/'actual-settid')]),
]

def main():
    started=time.monotonic()
    assert os.getuid()==1000 and os.getgid()==1000
    assert os.sched_getaffinity(0)=={6}
    limits={resource.RLIMIT_AS:1073741824,resource.RLIMIT_CPU:30,
            resource.RLIMIT_FSIZE:33554432,resource.RLIMIT_NOFILE:256,
            resource.RLIMIT_CORE:0}
    for kind,value in limits.items():
        assert resource.getrlimit(kind)==(value,value),(kind,resource.getrlimit(kind))
    assert not OUT.exists()
    for row in json.loads((HERE/'fixture-inputs.json').read_text())['rows']:
        path=Path(row['path'])
        assert path.is_file() and not path.is_symlink()
        raw=path.read_bytes()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],str(path)
    assert hashlib.sha256(HELPER.read_bytes()).hexdigest()==HELPER_SHA
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('settid_pinned_owned_capture',HELPER)
    h=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    assert available>=2*1024**3
    capacity=[]
    for path,floor in [('/home/holden/mckernel',16*1024**3),('/home/holden/mckernel-work/scratch',12*1024**3)]:
        st=os.statvfs(path);free=st.f_bavail*st.f_frsize
        capacity.append({'path':path,'available':free,'required':floor+128*1024**2})
        assert free>=floor+128*1024**2
    OUT.mkdir(mode=0o700)
    h.write(OUT/'admission.json',{'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','uid':os.getuid(),'affinity':sorted(os.sched_getaffinity(0)),'available_memory':available,'rlimits':limits,'capacity':capacity,'owned_capture_helper_sha256':HELPER_SHA})
    os.chdir(SOURCE)
    for number in h.STOP_SIGNALS:
        signal.signal(number,h.stop)
    rows=[]
    failure=None
    deadline=started+28
    try:
        remaining=deadline-time.monotonic()
        assert remaining>0
        signal.setitimer(signal.ITIMER_REAL,remaining)
        for label,argv in COMMANDS:
            remaining=deadline-time.monotonic()
            assert remaining>0 and h.cpu_used()<30
            path=OUT/label
            path.mkdir(mode=0o700)
            command={'label':label,'argv':argv,'cwd':str(SOURCE)}
            h.write(path/'command.json',command)
            # The root ordinary profile limits are already inherited. The
            # accepted helper masks fork->ownership, restores the child mask,
            # anchors WNOWAIT, retires before reap, joins, then closes streams.
            record=h.owned_capture(command,path,min(20,remaining),lambda:None)
            record.update(label=label,argv=argv)
            h.write(path/'whole.json',record)
            rows.append(record)
            assert record['returncode']==0 and record['direct_child_joined'] and record['group_absent'] and record['closed_streams'] and not record['error'] and not record['retirement_error'] and not record['timed_out'],(label,record)
            assert record['captures']['stderr']['size']==0,label
            assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())<=128*1024**2
        expected='PASS: 12 complete actual-C/actual-Rust settid cases; bytes/order/return/log/carrier\n'
        assert (OUT/'actual-12-cases/stdout').read_text()==expected
        assert h.cpu_used()<30 and time.monotonic()<=deadline
    except BaseException as exc:
        failure=type(exc).__name__+': '+str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
    result={'status':'PASS_FINITE_ACTUAL_C_RUST_SETTID_PARITY' if failure is None and len(rows)==5 else 'FAIL_STOPPED_PRESERVE_ALL','error':failure,'cases':12 if failure is None else None,'commands':len(rows),'rows':rows,'all_direct_joined':all(x['direct_child_joined'] for x in rows),'all_process_groups_absent':all(x['group_absent'] for x in rows),'closed_streams':all(x['closed_streams'] for x in rows),'seconds':time.monotonic()-started,'total_CPU_seconds':h.cpu_used(),'native_execution':False,'full_crate_link_default_retirement_proof':False}
    h.write(OUT/'result.json',result)
    print(json.dumps({k:result[k] for k in ('status','commands','seconds','total_CPU_seconds','error')},sort_keys=True))
    return 0 if result['status']=='PASS_FINITE_ACTUAL_C_RUST_SETTID_PARITY' else 1

if __name__=='__main__':raise SystemExit(main())
