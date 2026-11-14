"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Metadata-only diagnostic LONG admission data derivation; no root/query/test/workload."""
from pathlib import Path
import ast,copy,difflib,hashlib,json,sys
H=Path(__file__).resolve().parent;D=H.parent;B=D.parent/'runtime-sdk8-successor-1/admission-preparation-1'
E=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-diagnostic-collector-successor-1/admission-preparation-1')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(name,data):
 raw=(json.dumps(data,indent=2,sort_keys=True)+'\n').encode() if not isinstance(data,bytes) else data
 for root in [H,E]:
  with (root/name).open('xb') as f:f.write(raw)
 return ref(H/name)
def literal(source,key):
 n=next(n for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets))
 if isinstance(n.value,ast.Call):return {k.arg:ast.literal_eval(k.value) for k in n.value.keywords}
 return ast.literal_eval(n.value)
assert len(sys.argv)==3,'genuine new capsule acceptance + cohort source acceptance record paths required'
cap_review=ref(sys.argv[1]);cohort_review=ref(sys.argv[2])
c=copy.deepcopy(json.loads((B/'QUERY-INPUTS.json').read_bytes()));n=json.loads((D/'ROOT-SUCCESSOR-NAMESPACE.json').read_bytes());co=json.loads((D/'COHORT-BINDINGS.json').read_bytes());req=json.loads((D/'CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());stage=json.loads((D/'ACTUAL-DIAGNOSTIC-CASE-STAGE-BINDING.json').read_bytes())
physical=E.parent.parent/'runtime-sdk8-successor-1/retirement-preparation-1/physical-preparation-1/INDEPENDENT-ACTUAL-PHYSICAL-ACCEPTANCE.ROOT-RECORD.json'
assert ref(physical)['sha256']=='a68513c031ffe7470702ca53e7bb2b1a0a6e1fef8d5eb7dc420f9d3b8cccf249'
c['historical_SDK8_build_physical']=c['physical'];c['physical']=ref(physical);c['current_live_postjoin']=json.loads(physical.read_bytes());c['actual_capsule_stage']=stage['actual_handoff'];c['settlement_actual_cohort_fixture']=ref(D/'ACTUAL-DIAGNOSTIC-COHORT-FIXTURE-RECEIPT.json');c['settlement_stage_acceptance']=cap_review;c['settlement_independent_cohort_review']=cohort_review;c['controller']=ref(D/'capture_root_LONG.NOT-RELEASED.py');c['growth']=co['long_transport.py'];c['namespace']=ref(D/'ROOT-SUCCESSOR-NAMESPACE.json')
c['operation']=dict(HOST_parent=n['host_parent'],HOST_identity=dict(dev=n['host_identity']['device'],inode=n['host_identity']['inode'],uid=1000,mode=0o700),nonce=n['nonce'],capture_directory=req['capture_directory'],controller=c['controller'],future_release_path=n['release_path'],future_request_path=str(D/'CAPTURE-REQUEST.json'),manifest=ref(n['manifest_path']),runtime_files=co)
assert c['operation']['manifest']['sha256']=='27cfb26595556035995ace767d233ca4a71e3e6432f7ba0adb67c7a6f9025169'
source=(D/'source/native_diagnostic_container_owner.py').read_text();c['owner_constants']={k:literal(source,k) for k in ['CGROUP','EXTRA_READONLY','IMAGE','IMAGE_RECORD','IMAGE_RECORD_SHA256']}
c['prior_failed_nonce']='599bd7a0a4cb4e29b52d6ed0cc9aa0db';c['retained_previous_owner_evidence_paths'].append('/home/holden/mckernel-work/l12s8a1/p.owner-'+c['prior_failed_nonce']);c['retained_evidence_qualification']='All historical owner evidence retained, only prospective outputs requireabsence. Genuine failed599bd7 physicala685 suppliescurrentpostjoin; newcollector diagnosticnotrepair.';c['status']='DIAGNOSTIC_SDK8_FRESH_QUERY_PENDING_INDEPENDENT_ROOT_RELEASE'
pins={row['path']:row for row in c['pins']}
for row in [c[k] for k in ['physical','actual_capsule_stage','settlement_actual_cohort_fixture','settlement_stage_acceptance','settlement_independent_cohort_review','controller','growth','namespace']]+list(co.values())+[c['operation']['manifest']]:pins[row['path']]=row
c['pins']=list(pins.values());config=write('QUERY-INPUTS.json',c)
old=(B/'read_only_LONG_HOST_admission.py').read_text();query=old;node=next(n for n in ast.parse(query).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONFIG_SHA' for t in n.targets));query=query.replace(ast.get_source_segment(query,node),'CONFIG_SHA = '+repr(config['sha256']),1)
a=query.index(" need(f['physical']['verdict']==");z=query.index('\n',a)
query=query[:a]+" need(f['physical']['verdict']=='PASS_ACTUAL_FAILED_SDK8_LONG_599BD7_PHYSICAL_RETIREMENT_AND_CURRENT_POSTJOIN' and f['physical']['state']=='FAILED_SDK8_LONG_599BD7_POSITIVELY_RETIRED' and f['physical']['physical_clearance'] is True and f['physical']['current_live_postjoin']['sha256']=='4c10fe4b09f8a99f51a0f87f49c298da26ddc1cfe11453f2929cacddb0602920' and f['physical']['proc_sha256']=='9710013285f045ed411339ff127affdf490b80c480d4bcb22b8748ec679b0281' and f['physical']['mutex_sha256']=='5e8d2c1942ea3edf7ee6a623d19e2aea16bba50f1639c63fc1aff209b5641c20' and f['physical']['complete_publisher_free_snapshots']==2 and f['physical']['bound_client_identities']==23 and f['physical']['all_clients_outer_owner_absent'] is True and f['physical']['container_init']=={'pid':3925813,'start':None,'numerically_absent_both':True} and f['physical']['permanent_mutex']=='27:4' and f['physical']['eight_exclusion_paths_absent'] is True and f['physical']['normal_CID_removed_three_empty_queries_verified'] is True and f['physical']['native_acceptance'] is False,'actual failed SDK8 LONG599bd7 positivephysical/currentpostjoin')"+query[z:]
oldfn={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)};newfn={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(query).body if isinstance(n,ast.FunctionDef)};assert [k for k in oldfn if oldfn[k]!=newfn[k]]==['validate']
qref=write('read_only_LONG_HOST_admission.py',query.encode());runner=write('run_root_LONG_admission_capture.py',(B/'run_root_LONG_admission_capture.py').read_bytes());assert runner['sha256']=='522ef331dba4e84f45b2f2bc0965c0bb58490127154eb169f469da98619528bf'
profile=json.loads((B/'ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json').read_bytes());profile.update(capture_directory=str(H/'actual-fresh-root-admission-1'),input_sources=[qref,config],runner=runner,root_release=None);profile['query_argv'][-2:]=[qref['path'],qref['sha256']];prof=write('ROOT-FRESH-QUERY-PROFILE.NOT-RELEASED.json',profile)
argv=json.loads((B/'ROOT-FRESH-OBSERVER-ARGV.NOT-RELEASED.json').read_bytes());argv[-3:]=[runner['path'],prof['path'],prof['sha256']];ar=write('ROOT-FRESH-OBSERVER-ARGV.NOT-RELEASED.json',argv)
write('read-only-query-successor.diff',''.join(difflib.unified_diff(old.splitlines(True),query.splitlines(True),fromfile=str(B/'read_only_LONG_HOST_admission.py'),tofile=qref['path'])).encode())
facts=dict(scope=__doc__,status='DIAGNOSTIC_SDK8_ADMISSION_SOURCE_AND_FINALFACTS_READY_FOR_FOCUSED_REVIEW',source_query=qref,query_inputs=config,profile=prof,exact_argv=ar,operation=c['operation'],current_live_postjoin=c['current_live_postjoin'],actual_capsule_acceptance=cap_review,actual_cohort_acceptance=cohort_review,actual_cohort_fixture=c['settlement_actual_cohort_fixture'],query_functions_other_than_exact_physical_literal_predicate_AST_unchanged=True,runner_byte_identical=True,root_query_release=None,actual_query=None,fetched_source_publication=None,root_continuity=None,payload=None,independent_review=None,expiry=None,runtime_release=None,tests_root_probes_jobs=0)
print(json.dumps(write('FRESH-ADMISSION-PREPARATION-RECEIPT.json',facts)));print(json.dumps(write('EXECUTION-FACTS.PENDING-ROOT.json',facts)))
