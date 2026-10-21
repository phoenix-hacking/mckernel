"""Finite ordinary-profile check; dispatcher admission is required before execution."""
from pathlib import Path
import hashlib,json,os,resource,signal,subprocess,time

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'check-1'
RUSTC='/home/holden/mckernel-work/scratch/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/bin/rustc'
CC='/usr/bin/x86_64-linux-gnu-gcc-9'
COMMON=[CC,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fno-lto','-I',str(ROOT/'fixture-1')]
COMMANDS=[
 ('rust-object',[RUSTC,'--edition=2021','--crate-name','actual_settid_helper','--crate-type=lib','--emit=obj','-Dwarnings','-Cpanic=abort','-Copt-level=2','-Ccodegen-units=1','-Zthreads=1',str(ROOT/'fixture-1/actual-helper.rs'),'-o',str(OUT/'actual-helper.o')]),
 ('original-c',COMMON+['-c',str(ROOT/'fixture-1/original.c'),'-o',str(OUT/'original.o')]),
 ('candidate-c',COMMON+['-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS','-c',str(ROOT/'fixture-1/candidate.c'),'-o',str(OUT/'candidate.o')]),
 ('link',COMMON+['-no-pie',str(ROOT/'fixture-1/check.c'),str(OUT/'original.o'),str(OUT/'candidate.o'),str(OUT/'actual-helper.o'),'-Wl,--wrap=syscall_settid_body_result','-o',str(OUT/'actual-settid')]),
 ('actual-12-cases',[str(OUT/'actual-settid')]),
]

def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2,sort_keys=True)
        stream.write('\n')

def stop(signum,frame):
    raise InterruptedError('ordinary fixture stopped by signal %d'%signum)

def main():
    for number in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):
        signal.signal(number,stop)
    assert os.getuid()==1000 and os.getgid()==1000
    assert os.sched_getaffinity(0)=={6}
    limits={resource.RLIMIT_AS:1073741824,resource.RLIMIT_CPU:30,
            resource.RLIMIT_FSIZE:33554432,resource.RLIMIT_NOFILE:256,
            resource.RLIMIT_CORE:0}
    for kind,value in limits.items():
        assert resource.getrlimit(kind)==(value,value),(kind,resource.getrlimit(kind))
    assert not OUT.exists()
    inputs=json.loads((ROOT/'fixture-inputs.json').read_text())
    for row in inputs['rows']:
        path=Path(row['path'])
        assert path.is_file() and not path.is_symlink()
        raw=path.read_bytes()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],str(path)
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    assert available>=2*1024**3
    capacity=[]
    for path,floor in [('/home/holden/mckernel',16*1024**3),('/home/holden/mckernel-work/scratch',12*1024**3)]:
        st=os.statvfs(path);free=st.f_bavail*st.f_frsize
        capacity.append({'path':path,'available':free,'required':floor+128*1024**2})
        assert free>=floor+128*1024**2
    OUT.mkdir()
    save(OUT/'admission.json',{'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','uid':os.getuid(),'affinity':sorted(os.sched_getaffinity(0)),'available_memory':available,'rlimits':limits,'capacity':capacity})
    deadline=time.monotonic()+28
    rows=[]
    for label,cmd in COMMANDS:
        remaining=deadline-time.monotonic()
        assert remaining>3
        save(OUT/(label+'.command.json'),{'argv':cmd,'cwd':str(ROOT)})
        started=time.time_ns();mono=time.monotonic_ns();timedout=False
        with (OUT/(label+'.stdout')).open('xb') as stdout,(OUT/(label+'.stderr')).open('xb') as stderr:
            p=subprocess.Popen(cmd,cwd=ROOT,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','TZ':'UTC','MAKEFLAGS':'','CARGO_BUILD_JOBS':'1'},stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
            try:
                try:p.wait(timeout=min(20,remaining-3))
                except subprocess.TimeoutExpired:
                    timedout=True
                    os.killpg(p.pid,signal.SIGTERM)
                    try:p.wait(timeout=1)
                    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=1)
            finally:
                if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=1)
                try:os.killpg(p.pid,0);absent=False
                except ProcessLookupError:absent=True
                row={'argv':cmd,'pid':p.pid,'started_unix_ns':started,'finished_unix_ns':time.time_ns(),'elapsed_ns':time.monotonic_ns()-mono,'returncode':p.returncode,'direct_join':p.returncode is not None,'process_group_absent':absent,'timedout':timedout}
                save(OUT/(label+'.status.json'),row)
                rows.append(row)
        for suffix in ['stdout','stderr']:
            path=OUT/(label+'.'+suffix);data=path.read_bytes()
            save(OUT/(label+'.'+suffix+'.identity.json'),{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'device':path.stat().st_dev,'inode':path.stat().st_ino})
        assert p.returncode==0 and not timedout and absent,(label,row)
        assert (OUT/(label+'.stderr')).stat().st_size==0,label
        size=sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file())
        assert size<=128*1024**2
    expected='PASS: 12 complete actual-C/actual-Rust settid cases; bytes/order/return/log/carrier\n'
    assert (OUT/'actual-12-cases.stdout').read_text()==expected
    result={'status':'PASS_FINITE_ACTUAL_C_RUST_SETTID_PARITY','cases':12,'commands':len(rows),'all_direct_joined':all(x['direct_join'] for x in rows),'all_process_groups_absent':all(x['process_group_absent'] for x in rows),'native_execution':False,'full_crate_link_default_retirement_proof':False}
    save(OUT/'result.json',result)
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
