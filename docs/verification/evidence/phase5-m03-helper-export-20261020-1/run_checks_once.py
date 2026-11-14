from pathlib import Path
import importlib.util,json,os,resource,time,hashlib
D=Path(__file__).resolve().parent;O=D/'check-1'
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
s=importlib.util.spec_from_file_location('accepted_owned_capture',S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert os.sched_getaffinity(0)=={6} and resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());assert state['last_rate_limits']['primary']['usedPercent']<100 and state['phase']=='running' and state['stop_reason'] is None
sv=os.statvfs('/home/holden/mckernel-work/scratch');hv=os.statvfs(D);mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
assert hv.f_bavail*hv.f_frsize>=(16<<30)+(128<<20)+(640<<20) and sv.f_bavail*sv.f_frsize>=(12<<30)+(640<<20) and mem>=18<<30
# Fresh boot/UUID and active-record checks; no root or workload operation.
import subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
assert subprocess.run(['/usr/bin/findmnt','-n','-o','UUID','--target','/home/holden/mckernel-work/scratch'],check=True,capture_output=True,text=True).stdout.strip()=='2a5768c8-718d-4914-bdc0-6b32c5a92a52'
assert not os.path.lexists('/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock')
for row in json.loads((D/'INPUT-PINS.json').read_text()):
 raw=Path(row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
assert not O.exists();O.mkdir(mode=0o700);vectors=O/'vectors';vectors.mkdir(mode=0o700)
common=['/usr/bin/gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-fno-pie','-no-pie','-Wl,-z,noexecstack','-DND_M03_MPROTECT_UNALIGNED']
commands=[('compile-actual-body-fixture',common+[str(D/'test_helper_export.c'),'-o',str(O/'fixture')],10),('actual-body-fixture',[str(O/'fixture'),str(vectors)],10),('compile-current-collector',common+['-static',str(D/'candidate/native_diagnostic_guest_collector.c'),'-o',str(O/'collector')],10)]
records=[];begin=time.monotonic()
def limits():
 resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(32<<20,32<<20));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
for label,argv,wall in commands:
 p=O/label;p.mkdir(mode=0o700);m.write(p/'command.json',{'argv':argv});r=m.owned_capture({'argv':argv},p,wall,limits);records.append(r)
 if r['returncode']!=0 or not r['direct_child_joined'] or not r['group_absent'] or m.cpu_used()>30 or time.monotonic()-begin>30:break
 if label=='actual-body-fixture':
  frames={name:json.loads((vectors/name).read_text().split(' ',1)[1]) for name in ['missing-main.frame','empty-main.frame','success.frame','frame-cap-omission.frame']}
  assert frames['missing-main.frame']['helper']=='boot' and frames['missing-main.frame']['raw_wait_status']==256 and bytes.fromhex(frames['missing-main.frame']['streams']['stderr']['hex'])==b'modeled failure\n'
  assert frames['empty-main.frame']['helper']=='load-mcctrl' and frames['empty-main.frame']['evidence_fault']==1 and frames['empty-main.frame']['raw_wait_status']==0
  assert (vectors/'success.frame').read_bytes().startswith(b'ND_PAYLOAD ') and b'ND_HELPER_FAIL' not in (vectors/'success.frame').read_bytes()
  assert frames['frame-cap-omission.frame']['frame_streams_omitted'] is True and frames['frame-cap-omission.frame']['captured_stdout_bytes']==1024 and frames['frame-cap-omission.frame']['captured_stderr_bytes']==1024
  assert frames['frame-cap-omission.frame']['streams']['stdout']['hex']==frames['frame-cap-omission.frame']['streams']['stderr']['hex']=='' and (vectors/'unsafe.frame').read_bytes()==b''
  m.write(O/'FOCUSED-FIVE-CASE-RESULT.json',dict(status='PASS_ACTUAL_HELPER_EXPORT_BODIES',cases=['missing-main','empty-main','success-no-spurious-frame','invalid-cap-and-full-frame-budget','unsafe-handoff'],modeled_helper_bytes=True,historical_failed_helper_identity=None,success_oracle_modified=False))

ok=len(records)==3 and all(r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] for r in records)
if ok:(O/'collector').chmod(0o700)
m.write(O/'whole.json',dict(status='PASS_CURRENT_COLLECTOR_AND_EXACT_HELPER_FAILURE_EXPORT_BODY' if ok else 'FAIL_STOP_PRESERVE',records=records,elapsed_seconds=time.monotonic()-begin,CPU_seconds=m.cpu_used(),guest_runs=0))
print(json.dumps(dict(status='PASS' if ok else 'FAIL',records=len(records),elapsed_seconds=time.monotonic()-begin)));raise SystemExit(0 if ok else 1)
