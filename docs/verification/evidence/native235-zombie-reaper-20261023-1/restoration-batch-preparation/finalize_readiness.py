"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Small source/data readiness evidence only, no archive/stage/runtime effects.
"""
from pathlib import Path
import ast,hashlib,json
D=Path(__file__).resolve().parent;A=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-sdk-successor-20261023-1/restoration-batch-preparation');Z=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/zombie-sdk-native-successor-1');B=Path('/home/holden/mckernel-work/host-preparation/p-m05-fixed-profile-batch-adaptation-20261023-1');OLD=Path('/home/holden/mckernel-work/host-preparation/p-m05-v3-matched-first-restoration-binding-20261023-1/runtime-first-restoration-1')
def j(p):return json.loads(p.read_text())
def ref(p):
 r=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(r).hexdigest(),bytes=len(r))
def write(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
for p in [A/'derive_fixed_batch.py',A/'join_restoration_batch_receipts.py',A/'run_ten_cycles.py']:ast.parse(p.read_text())
capture=j(D/'AUTHORITY-CHECK-ACTUAL-CAPTURE-2.json');assert capture['status']=='COMPLETED'and capture['wait_status']==dict(kind='exited',code=0)and capture['cleanup_complete']
assert 'Ran 8 tests' in (D/'receipt-tests.stderr').read_text()and (D/'receipt-tests.stderr').read_text().rstrip().endswith('OK')
record=dict(scope=__doc__.splitlines()[0],status='SOURCE_BOUND_CURRENT_TUPLE_RESTORATION_STAGE_READY_AND_TEN_CYCLE_CONSTANT_DERIVATION_PREPARED_NOT_RUNTIME_RELEASED',
next_actual_227_command=j(Z/'case-227/OVERLAY-ARGV.ACTUAL.json'),next_actual_restoration_stage_command=j(A/'stage-binding/READY-ACTUAL-P05-STAGE-ARGV.json'),
current_tuple=dict(sdk_acceptance=ref(Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/sdk-build-release/INDEPENDENT-ACTUAL-SDK-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.json')),mcctrl_sha256='d8d8c4a0b004f64d2c7aceb98c2bed337996bc955a419d1ebfa51f184451b9bc',image_sha256='10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2',launcher_sha256='dca0250159ce04a272a72dd1217213a4b6e0f21ec8c21da211eede250c451954'),
source_dependency_delta=dict(stager=ref(A/'stage-binding/stage_m05_two_generation.py'),binding=ref(A/'stage-binding/BINDING.json'),explicit_authority_profile='current68-zombie-reaper-build-link-physical',changed_tuple_member='modules/mcctrl.ko',unchanged_previous_V3_stage_members=61,unchanged_original_baseline_members=57,strict_oracles_unchanged=['f043collector','40Bsignal-mask stdout/empty stderr/exit0','4312 firstboot/1a7 secondboot','twofresh owner epochs0,1,1and0,2,2','exact62member namespace'],prior_five_runtime_source_cohort=ref(OLD/'EXACT-FIVE-SOURCE-COHORT.json'),runtime_delta_after_actual_stage=['newstage manifest path/hash in case_evaluator','sibling paths/hash pins in four runtime sources and owner SOURCE_HASHES','new exactnonce/metadata/capture/root operation bindings; original evaluation logic unchanged']),
batch_dependency_delta=dict(existing_parent=ref(B/'native_diagnostic_batch.py'),existing_hooks=ref(B/'production-adapter-1/production_hooks.py'),existing_null_slot=ref(B/'production-adapter-1/FUTURE-PROFILE-SLOT.json'),deriver=ref(A/'derive_fixed_batch.py'),changed_parent_assignments_only=['PROFILE_ID','MANIFEST_SHA','AUTHORITY_SHA'],proofs_that_stay_absent_until_actual_acceptance=['matchingprofile sdk acceptance wrapper','matchingprofile launcher acceptance wrapper','matchingprofile firstcomplete restoration wrapper'],ordered_case_count=10,old_cycle_credit=0,release=None),
receipt_join=ref(A/'join_restoration_batch_receipts.py'),ten_cycle_caller=ref(A/'run_ten_cycles.py'),
cheap_observations=dict(authority_count=8,actual_capture=ref(D/'AUTHORITY-CHECK-ACTUAL-CAPTURE-2.json'),elapsed_seconds=capture['elapsed_seconds'],receipt_join_regressions=8,receipt_tests_stderr=ref(D/'receipt-tests.stderr'),receipt_scope='Actual join code with synthetic receipts; not native evidence.'),
first_actual_stage=None,first_complete_restoration=None,ten_cycle_result=None,execution_review=None,native_runs=0,
failure_family=dict(authority_source_failures=0,capture_failed_candidate=1,capture_bounded_correction=1,cause='System Python lacks os.waitstatus_to_exitcode; accepted Python3.9 fixed capture only, freshnamespace. First consumer already exited0; originalcapture preserved.'),
readiness='Root fresh235 outcome+physical then227; explicit stager source review+ordinary stage grant next. No live workload/probe by this lane. Actual stage manifest needed before runtime source derivatives/first-restoration release. Actual first independent review+inner result hash/current initrd join needed before fixed ten-cycle profile derivation; Hooks separately requires exact three reviewed profile/tuple wrappers and ordered release.')
write(D/'CURRENT-TUPLE-RESTORATION-AND-BATCH-DEPENDENCIES.json',record)
for name in ('derive_fixed_batch.py','join_restoration_batch_receipts.py','run_ten_cycles.py'):
 dst=D/name;dst.write_bytes((A/name).read_bytes())
print(json.dumps(dict(status=record['status'],authority_checks=8,receipt_join_checks=8,stage_source=record['source_dependency_delta']['stager'])))
