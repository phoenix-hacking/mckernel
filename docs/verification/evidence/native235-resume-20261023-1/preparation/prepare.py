"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source/metadata preparation; never executes root, Docker, guest or guard argv.
"""
import ast,hashlib,json,os
from pathlib import Path
assert os.sched_getaffinity(0)=={7}
D=Path(__file__).resolve().parent
B=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1')
C=B/'fork-v3-matched-process-successor-1/case-235';F=C/'final-runtime-ready-1';A=F/'root-live-admission-1'
T=Path('/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/actual-terminal-preparation-1')
def read(p):return json.loads(p.read_text())
def ref(p,sha=None):
    raw=p.read_bytes();r=dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    if sha:assert r['sha256']==sha,(str(p),r)
    return r
h=read(F/'FINAL-ACTUAL-V3-NATIVE235-READY-HANDOFF.json');a=read(A/'ROOT-EXACT-READONLY-ADMISSION-OPERATION-1.json');op=read(C/'NATIVE-OPERATION.ACTUAL.json')
assert ref(A/'read_only_native235_admission.py')['sha256']=='3dd230d35c41011e84b13cecef9ab303586c02ada9b0259fa50487d16d79b05b'
assert a['argv'][-1]==str(A/'read_only_native235_admission.py')
assert read(F/'EXACT-PRODUCTION-GUARD-ARGV.json')==h['production_guard']['argv']
assert op['argv']==h['owner_argv'] and op['actual_release'] is None and op['fresh_root_admission'] is None
assert h['strict_oracle']['stdout']['bytes']==235 and h['strict_oracle']['exit_code']==0 and h['strict_oracle']['stderr']['bytes']==0
assert h['nonce']=='8646cb69db21440ca31573ab1b3d0691'
refs={}
for key in ('manifest','actual_stage_consumer_join','native_operation','native_capture_argv_descriptor','source_publication_map','strict_consumer_capture'):
    r=h[key];refs[key]=ref(Path(r['path']),r['sha256']);assert refs[key]['bytes']==r['bytes']
for key in ('argv_descriptor','data'):
    r=h['production_guard'][key];refs['production_guard_'+key]=ref(Path(r['path']),r['sha256'])
refs['final_handoff']=ref(F/'FINAL-ACTUAL-V3-NATIVE235-READY-HANDOFF.json')
refs['admission_source']=ref(A/'read_only_native235_admission.py',a['source']['sha256'])
refs['admission_operation']=ref(A/'ROOT-EXACT-READONLY-ADMISSION-OPERATION-1.json')
refs['physical_retirement']=ref(T/'INDEPENDENT-ACTUAL-LAUNCHER-PHYSICAL-ACCEPTANCE-1.json')
assert refs['physical_retirement']['sha256'].startswith('46ed040d')
physical=read(T/'INDEPENDENT-ACTUAL-LAUNCHER-PHYSICAL-ACCEPTANCE-1.json')
assert physical['status']=='PASS_ACTUAL_LAUNCHER_PHYSICAL_RETIREMENT' and physical['physical_clearance'] is True
refs['retained_live_postjoin_observer']=ref(T/'ACTUAL-CURRENT-LIVE-POSTJOIN-OBSERVATION-1.json')
assert read(T/'ACTUAL-CURRENT-LIVE-POSTJOIN-OBSERVATION-1.json')['current_live_postjoin']['observer_release'] is not None
refs['service_resolution']=ref(Path('/home/holden/mckernel/docs/verification/os-milestones-20260914/USER-SERVICE-RESOLUTION-20261023.json'))
for p in (A/'read_only_native235_admission.py',B/'native-runtime-ready-1/capture_native199_owner.py'):
    ast.parse(p.read_text());refs[p.name]=ref(p)
p=dict(scope=__doc__.splitlines()[0],status='PREPARED_EXACT_NATIVE235_PENDING_FRESH_ROOT_RESULTS_AND_ONE_SHOT_REVIEW',references=refs,
read_only_admission_argv=a['argv'],metadata_publication_argv=h['metadata_publication']['argv'],production_guard_argv=h['production_guard']['argv'],native_capture_argv=h['next_native_capture_argv'],owner_argv=h['owner_argv'],strict_oracle=h['strict_oracle'],profile=h['native_profile'],nonce=h['nonce'],metadata_parent='/home/holden/mckernel-work/scratch/n235v1',
required_fresh_bindings=dict(root_read_only_admission=None,metadata_identity_and_closed_capture=None,production_guard_closed_capture=None,current_source_tool_backend_identity_and_fetched_checkpoint=None,independent_execution_review=None,one_shot_execution_release=None),
retained_observer_rule='Existing observer release is non-null and bound here; historical read-only observer is not fresh root admission or post-cleanup authority. Positive physical acceptance separately bound.',
conditional_execution_rule='Exact existing native capture/owner argv only after fresh root admission, exclusive metadata publication/identity, actual guard PASS, current source/tool/artifact identities and independent one-shot release. No expired or original failed235 release.',
geometry_rule='Admission pins original110GiB/inode47468427/UUID; no geometry mutation is authorized here. If root geometry changed, preserve refusal and prepare a separately reviewed coherent successor.',
failure_history='Prior235 failed missing pool-query/child-scheduling/WAIT-exit bridge. New SDK/launcher accepted and actual launcher physical retirement46ed040d accepted. Do not replay failed old inputs. This lane has no new candidate/runtime attempts.',
next_observations=['strict235B native result plus physical retirement','separate227 recovery case and release','first matched V3 complete restoration'],
stop='Any new service/auth/policy error: preserve and stop; no retry/bypass. No root/Docker/guest execution by preparer.',native_acceptance=False,native_execution_authorized=False)
(D/'EXACT-NATIVE235-CONDITIONAL-PACKET.json').write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
(D/'READONLY-ADMISSION-ARGV.json').write_text(json.dumps(a['argv'],indent=2)+'\n')
(D/'PREPARATION-RECEIPT.json').write_text(json.dumps(dict(status='PASS_EXACT_STATIC_REFERENCE_AND_ARGV_JOIN',references_checked=len(refs),physical_retirement_sha256=refs['physical_retirement']['sha256'],root_Docker_guest_executions=0,native_credit=0,fresh_root_result=None),indent=2)+'\n')
print(json.dumps(dict(status='PASS_EXACT_STATIC_REFERENCE_AND_ARGV_JOIN',references_checked=len(refs),physical_sha256=refs['physical_retirement']['sha256'])))
