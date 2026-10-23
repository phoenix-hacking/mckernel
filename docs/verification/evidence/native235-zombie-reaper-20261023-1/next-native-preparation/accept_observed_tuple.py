"""Functional OS only; no security testing. Accept bound artifact facts in metadata; no stage."""
from pathlib import Path
import copy,hashlib,json
E=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-sdk-successor-20261023-1/next-native-preparation');V=H/'accepted-mcctrl-only-1';V.mkdir(mode=0o700);S=V/'future-runtime-metadata';S.mkdir(mode=0o700)
O=H/'mcctrl-only-observed-1/future-runtime-metadata';F=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/zombie-sdk-native-successor-1')
A=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/sdk-build-release/INDEPENDENT-ACTUAL-SDK-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.json');assert hashlib.sha256(A.read_bytes()).hexdigest()=='5df70b4414fe418e73b3e01650380ecf58d7a085642cce95b94c611a1a0d9189';accept=json.loads(A.read_text());assert accept['status']=='PASS'
def load(p):return json.loads(p.read_text())
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,d):p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
for p in O.rglob('*'):
 if p.is_file():q=S/p.relative_to(O);q.parent.mkdir(mode=0o700,parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
p=S/'PRODUCER-ONE-MODULES.PENDING.json';d=load(p);d.update(status='ACCEPTED_ACTUAL_SDK3_TUPLE_WITH_ONLY_MCCTRL_RUNTIME_DELTA',sdk_independent_artifact_acceptance=ref(A),sdk_physical_retirement=ref(A));save(p,d)
for n in ['235','227']:
 p=S/('case-'+n)/'CASE-DATA.PENDING.json';d=load(p);d.update(status='ACCEPTED_REPAIRED_SDK_TUPLE_PENDING_BASE_OVERLAY_AND_FRESH_NATIVE_RELEASE');d['producer']=dict(ref(S/'PRODUCER-ONE-MODULES.PENDING.json'),path=str(F/'PRODUCER-ONE-MODULES.PENDING.json'));d['fresh_authorities']['matched_artifact_acceptance']={'sdk':ref(A),'launcher':load(S/'PRODUCER-ONE-MODULES.PENDING.json')['launcher_acceptance'],'status':'DATA_JOIN_GENUINE_INDEPENDENT_ACCEPTANCES'};save(p,d)
p=S/'NEXT-NATIVE-READY.PENDING.json';d=load(p);d.update(status='ACCEPTED_SDK_TUPLE_PENDING_ROOT_ORDINARY_STAGE_GRANT',owned_host_preparation=str(V),SDK_actual_artifact_acceptance=ref(A));d['producer']=dict(ref(S/'PRODUCER-ONE-MODULES.PENDING.json'),path=str(F/'PRODUCER-ONE-MODULES.PENDING.json'));d['cases']=[dict(ref(S/('case-'+n)/'CASE-DATA.PENDING.json'),path=str(F/('case-'+n)/'CASE-DATA.PENDING.json'))for n in ['235','227']];save(p,d)
# One artifact-bound stable snapshot argv and existing generic supervised caller.
snapshot=load(S/'ONE-EXCLUSIVE-RUNTIME-SNAPSHOT-ARGV.PENDING.json')[0];save(S/'SNAPSHOT-ARGV.ARTIFACT-BOUND.json',snapshot['fullargv'])
caller=(S/'case-235/run-overlay.PENDING.py').read_text().replace('OVERLAY-ARGV.ACTUAL.json','SNAPSHOT-ARGV.ARTIFACT-BOUND.json').replace('actual-v3-overlay-capture-1','actual-mcctrl-snapshot-capture-1').replace('ACTUAL-V3-OVERLAY-CAPTURE-RESULT.json','ACTUAL-MCCTRL-SNAPSHOT-CAPTURE-RESULT.json').replace('V3 235 overlay','new mcctrl stable snapshot');(S/'run-snapshot.ARTIFACT-BOUND.py').write_text(caller)
# Existing generic one-record patch runs after snapshot receipt binding.
argv=load(S/'ONE-RECORD-PATCH-ARGV.PENDING.json');save(S/'ONE-RECORD-PATCH-ARGV.ARTIFACT-BOUND.json',argv)
caller=(S/'run-one-record-patch.PENDING.py').read_text().replace('ONE-RECORD-PATCH-ARGV.ACTUAL.json','ONE-RECORD-PATCH-ARGV.ARTIFACT-BOUND.json');(S/'run-one-record-patch.ARTIFACT-BOUND.py').write_text(caller)
print(json.dumps({'accepted_source':str(S),'acceptance':ref(A),'status':d['status']}))
