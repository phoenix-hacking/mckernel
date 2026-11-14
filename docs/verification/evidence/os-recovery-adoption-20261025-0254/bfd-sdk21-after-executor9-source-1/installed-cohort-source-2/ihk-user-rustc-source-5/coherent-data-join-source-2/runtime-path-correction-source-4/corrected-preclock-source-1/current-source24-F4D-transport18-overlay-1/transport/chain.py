"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing direct query -> actual wait -> unchanged complete group/client absence -> sudo prepare lifecycle.
No outer query timeout/CPU limit, no kill controller, no SDK/owner/final release publication.
"""
from pathlib import Path
import json,hashlib,os,sys,time,subprocess,importlib.util
D=Path(__file__).parent;A=D/'admission-preparation-source24-bound-1';C=A/'root-readonly-admission-capture-1'
FILL_REF = None
ENTRY_REF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4/corrected-preclock-source-1/direct_query_entry.SOURCE24-FETCH-BOUND.py', 'bytes': 2494, 'sha256': 'c17e68483303231161a66a4ef1b8047223a8c94047e21b9095ea1c71faa99d6f'}
QUERY_REF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4/corrected-preclock-source-1/admission-preparation-source24-bound-1/run_root_sdk_readonly_admission.py', 'bytes': 17101, 'sha256': '3ce2ccddbcaa058d24123813dcebb801e38569c11ed57c91113380180ff5b19f'}
INPUTS_REF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4/corrected-preclock-source-1/admission-preparation-source24-bound-1/QUERY-INPUTS.ROOT.json', 'bytes': 383, 'sha256': '3fef1e2c1a3c8902d34280c160765360c33d843ec8378489f448ebcb699ffeb8'}
REQUEST_REF = {'bytes': 4270, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4/REQUEST.BFD.UNUSED-NONCE.PENDING-RELEASE.json', 'sha256': '44e2572636ddd678759abb854e601c145dfc99183d356b06228572d7ae11954e'}
FETCH_SHA = None
APPROVAL_SHA = None
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert os.getuid()==os.geteuid()==os.getgid()==1000
assert sys.argv[1:]==[hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
assert FILL_REF is not None, 'genuine fresh-overlay-bound finalfill source required before query'
for ref in (FILL_REF,ENTRY_REF,QUERY_REF,INPUTS_REF,REQUEST_REF):
 raw=Path(ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('readonly_census_only',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
assert not os.path.lexists(C) and not os.path.lexists(A/'root-readonly-admission-preview-1')
assert not os.path.lexists(D/'root-query-export-1') and not os.path.lexists(D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json')
C.mkdir(mode=0o700)
begin=time.monotonic()
p=subprocess.Popen(['/home/holden/anaconda3/bin/python3','-I','-B',ENTRY_REF['path']],stdin=subprocess.DEVNULL)
rc=p.wait() # Actual creator joins the samePID exec. Intentionally no timeout and no query CPU rlimit.
joined=time.monotonic()
h.write(C/'ACTUAL-DIRECT-CHILD-EXIT.json',dict(pid=p.pid,returncode=rc,direct_child_joined=True,query_seconds=joined-begin,provenance='actual subprocess.Popen/wait; no h990 owned_capture'))
assert rc==0
birth=json.loads((C/'DIRECT-PROCESS-BEFORE-EXEC.json').read_bytes());assert birth['pid']==p.pid
assert not Path('/proc/'+str(p.pid)).exists() and h.members(birth['pgid'])==[]
q=json.loads((A/'root-readonly-admission-preview-1/ADMISSION.json').read_bytes())
assert q['status']=='PASS_READONLY_SDK_CAPACITY_IDENTITY_IMAGE_ONLY' and q['target_calls']==q['container_create_calls']==0
clients=[]
for path in sorted((A/'root-readonly-admission-preview-1').glob('command-*/status.json')):
 row=json.loads(path.read_bytes());assert row['state']=='exited' and row['exit_code']==0 and type(row['pid']) is int
 assert not Path('/proc/'+str(row['pid'])).exists() and h.members(row['pid'])==[]
 clients.append(dict(status_path=str(path),pid=row['pid'],recorded_birth=None,source_record_has_no_birth=True,pid_absent=True,group_absent=True))
assert clients and all(c['empty'] is True and c['surviving_members']==[] for c in q['group_checks'])
h.write(C/'ACTUAL-DIRECT-EXIT-AND-CLIENT-ABSENCE.json',dict(direct_process=birth,actual_direct_child_wait_returncode=rc,direct_pid_absent=True,direct_group_absent=True,client_checks=clients,h990_owned_capture_used=False,outer_timeout=None,outer_CPU_rlimit=None))
result=dict(schema='mckernel.direct-entry.query-terminal-and-postjoin.v1',provenance='actual parent Popen/wait + samePID record + source990 complete proc/group/clientPIDabsence; no h990 owned_capture',returncode=rc,seconds=joined-begin,pid=p.pid,start=int(birth['starttime']),direct_child_joined=True,group_absent=True,closed_streams=True,error=None,retirement_error=None,timed_out=False,remaining_group_members=[],unexpected_group_members=[],captures={k:h.hashed(C/k,32<<20) for k in ('stdout','stderr')})
assert result['captures']['stderr']['size']==0
h.write(A/'ROOT-READONLY-ADMISSION-WHOLE-JOIN.json',result)
argv=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',FILL_REF['path'],'--prepare-review-payload',FETCH_SHA,APPROVAL_SHA]
h.write(C/'EXACT-ROOT-PREPARE-ARGV.json',dict(argv=argv,query_outer_timeout=None,query_outer_CPU_rlimit=None))
with (C/'prepare.stdout').open('xb') as out,(C/'prepare.stderr').open('xb') as err:
 prepared=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
 out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
h.write(C/'ACTUAL-PREPARE-EXIT.json',dict(returncode=prepared.returncode,postjoin_and_prepare_seconds=time.monotonic()-joined,query_age_seconds=time.time()-q['at'],captures={k:h.hashed(C/('prepare.'+k),32<<20) for k in ('stdout','stderr')}))
assert prepared.returncode==0 and (C/'prepare.stderr').stat().st_size==0
raw=(C/'prepare.stdout').read_text();value=json.loads(raw)
assert value['status']=='PAYLOAD_FOR_INDEPENDENT_REVIEW_NOT_EXECUTION_RELEASE'
print(raw,end='',flush=True)
