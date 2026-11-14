"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Metadata/source-only binding of accepted single read-only LONG admission algorithm.
"""
import ast,hashlib,json,difflib,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;P=D/'admission-preparation-1';P.mkdir(mode=0o700)
B=D.parent/'expert-controller-binding-repair-1/admission-preparation-1'
R=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/runtime-sdk6-successor-1')
def descriptor(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 with p.open('x') as f:f.write(json.dumps(v,sort_keys=True,indent=2)+'\n')
def literal(source,key):
 v=next(n.value for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets))
 if isinstance(v,ast.Call):return {k.arg:ast.literal_eval(k.value) for k in v.keywords}
 return ast.literal_eval(v)
c=json.loads((B/'QUERY-INPUTS.json').read_bytes());n=json.loads((D/'ROOT-RESERVED-NAMESPACE.json').read_bytes());cohort=json.loads((D/'COHORT-BINDINGS.json').read_bytes());req=json.loads((D/'CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes())
physical=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/eventfd-sdk-preparation-6/postbuild-physical-preparation-1/INDEPENDENT-ACTUAL-SDK6-PHYSICAL-ACCEPTANCE.ROOT-RECORD.json')
assert descriptor(physical)['sha256']=='febfc23cc42035ce08482f3609c0b629dd446e0f0f9c96e67228cb4feb1d33b0'
c['historical_DFBB_physical']=c['physical'];c['historical_AA5_pre_effect_retirement']=c.pop('latest_pre_effect_retirement');c['historical_AA5_current_live_postjoin']=c['current_live_postjoin']
c['physical']=descriptor(physical);c['current_live_postjoin']=json.loads(physical.read_bytes())
c['SDK6_artifact_acceptance']=descriptor('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/eventfd-sdk-preparation-6/postbuild-preparation-1/INDEPENDENT-ACTUAL-SDK6-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.ROOT-RECORD.json')
assert c['SDK6_artifact_acceptance']['sha256']=='9159dcbd13c816f50d42390a05223e08a479b5f85d8183c4f61579bda20bc176'
c['actual_capsule_stage']=descriptor('/home/holden/mckernel-work/host-preparation/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/eventfd-next-native-preparation-1/capsule-next-1/ACTUAL-SDK6-CAPSULE-AND-STRICT-LOADER-HANDOFF.json')
c['controller']=descriptor(D/'capture_root_LONG.NOT-RELEASED.py');c['growth']=cohort['long_transport.py'];c['SDK6_actual_cohort_fixture']=descriptor(D/'ACTUAL-SDK6-COHORT-FIXTURE-RECEIPT.json');c['namespace']=descriptor(D/'ROOT-RESERVED-NAMESPACE.json')
c['operation']=dict(HOST_parent=n['HOST_parent'],HOST_identity=n['HOST_identity'],nonce=n['nonce'],capture_directory=req['capture_directory'],controller=c['controller'],future_release_path=n['scratch_release'],future_request_path=str(D/'CAPTURE-REQUEST.json'),manifest=descriptor(n['scratch_manifest']),runtime_files=cohort)
s=(D/'source/native_diagnostic_container_owner.py').read_text();c['owner_constants']={k:literal(s,k) for k in ['CGROUP','EXTRA_READONLY','IMAGE','IMAGE_RECORD','IMAGE_RECORD_SHA256']}
c['prior_failed_nonce']='91c61b415b1a4a9c9c00bcde727ee33a'
c['retained_previous_owner_evidence_paths'].append('/home/holden/mckernel-work/native-runs/l12c1/p.owner-'+c['prior_failed_nonce'])
c['retained_evidence_qualification']='Historical owner/evidence directories remain retained; only current prospective output paths require absence. Current physical authority is SDK6 febfc under root continuity; prior records retain historical scope.'
c['expert_controller_source_review']=None;c['SDK6_independent_cohort_source_review']=None;c['status']='FROZEN_SDK6_FRESH_QUERY_PENDING_INDEPENDENT_ROOT_RELEASE_NO_EXECUTION'
# Preserve historical input pins and append all precise new metadata; no large archive hashing.
pins={row['path']:row for row in c['pins']}
for row in [c[k] for k in ['physical','SDK6_artifact_acceptance','actual_capsule_stage','controller','growth','SDK6_actual_cohort_fixture','namespace']]+list(cohort.values())+[c['operation']['manifest']]:pins[row['path']]=row
c['pins']=list(pins.values());write(P/'QUERY-INPUTS.json',c)
source=(B/'read_only_LONG_HOST_admission.py').read_text();old=source
source=source.replace("CONFIG_SHA = '8ccf5efadac5bc5b2b445b0f971ea995e1be8ea43f77ded573a08de8efbbb1ae'",'CONFIG_SHA = '+repr(descriptor(P/'QUERY-INPUTS.json')['sha256']))
start=source.index(" need(f['physical']['verdict']==");end=source.index('\n',start)
source=source[:start]+" need(f['physical']['verdict']=='PASS_ACTUAL_SDK6_PHYSICAL_RETIREMENT_AND_CURRENT_POSTJOIN' and f['physical']['current_live_postjoin']=='SDK6_BUILD_POSITIVELY_RETIRED' and f['physical']['physical_clearance'] is True and f['physical']['root_uninterrupted_continuity'] is True and f['physical']['owner_pid']==3838054 and f['physical']['owner_start']==57597269 and f['physical']['owner_all15_clients_absent_both'] is True and f['physical']['clients_reaped']=={'Docker':14,'admission':1} and f['physical']['container_removed_three_empty_queries'] is True and f['physical']['permanent_mutex']=='27:4' and f['physical']['eight_paths_absent'] is True and f['physical']['publishers']==[],'actual SDK6 positive physical/current postjoin')"+source[end:]
source=source.replace("p['children']==[],'fresh private HOST LONG parent exists empty UID1000 mode700'", "p['children']==[] and p['dev']==c['operation']['HOST_identity']['dev'] and p['ino']==c['operation']['HOST_identity']['inode'],'fresh exact private HOST LONG parent exists empty UID1000 mode700'")
source=source.replace('Retained prior-owner evidence is pinned by physicala1cd; only prospective outputs require absence.','Retained prior-owner evidence remains historical; SDK6 febfc is current physical authority. Only prospective outputs require absence.')
with (P/'read_only_LONG_HOST_admission.py').open('x') as f:f.write(source)
shutil.copy2(B/'run_root_LONG_admission_capture.py',P/'run_root_LONG_admission_capture.py')
profile=json.loads((B/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json').read_bytes());profile['capture_directory']=str(P/'actual-fresh-root-admission-1');profile['input_sources']=[descriptor(P/'read_only_LONG_HOST_admission.py'),descriptor(P/'QUERY-INPUTS.json')];profile['runner']=descriptor(P/'run_root_LONG_admission_capture.py');profile['query_argv'][-2:]=[str(P/'read_only_LONG_HOST_admission.py'),descriptor(P/'read_only_LONG_HOST_admission.py')['sha256']];profile['root_release']=None;write(P/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json',profile)
argv=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--core=0:0','--nofile=256:256','--','/home/holden/anaconda3/bin/python3','-I','-B',profile['runner']['path'],str(P/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json'),descriptor(P/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json')['sha256']]
write(P/'ROOT-FRESH-OBSERVER-ARGV.NOT-RELEASED.json',argv)
(P/'read-only-query-successor.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile='accepted-AA5-fresh-query',tofile='SDK6-data-bound-fresh-query')))
receipt=dict(scope=__doc__,status='FROZEN_SINGLE_READ_ONLY_SDK6_ADMISSION_SOURCE_PENDING_INDEPENDENT_RELEASE',files={p.name:descriptor(p) for p in P.iterdir() if p.is_file()},unchanged_runner_sha256=profile['runner']['sha256'],current_live_postjoin='SDK6_BUILD_POSITIVELY_RETIRED',physical=c['physical'],source_changes=['CONFIG_SHA','Exact SDK6 physical data/schema predicate','Exact reserved HOST dev/inode additional predicate','Historical evidence comment'],unchanged=['collect/read-only algorithms','engine59ef complete two-snapshot census','mutex27:4 and eight ownership paths','NONE daemon identity','d91d full growth/floors/reserves','CPU7/2GiB/30CPU/60wall+6/32MiB/NOFILE256/core0 owned990807 profile and signal registration'],source_profile_review=None,root_query_release=None,actual_fresh_query=None,root_execution_release=None,native_acceptance=False)
write(P/'FRESH-ADMISSION-PREPARATION-RECEIPT.json',receipt)
shutil.copytree(P,R/P.name);shutil.copy2(Path(__file__),R/Path(__file__).name)
print(json.dumps(descriptor(P/'FRESH-ADMISSION-PREPARATION-RECEIPT.json'),sort_keys=True))
