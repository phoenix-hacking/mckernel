"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
PROPOSED Root-invoked source-only data fill; never grants or enters native runtime.
Uses released227 document keys and existing actual validators, never dummy authorities.
"""
from pathlib import Path
import argparse,copy,datetime,hashlib,importlib.util,json,re

HERE=Path(__file__).resolve().parent
COHORT=HERE.parent
E=COHORT.parent.parent.parent
BASE=E/'m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1'
REVIEW=E/'new-window-observer-guard-independent-review-20261028-1/ORIGINAL227-ROOT61-REVIEW-1'
FINALIZER=COHORT/'finalizer-window-clamp-correction-source-1/finalize_original227_window_bound.py'
CASE='P-M01-02-child-SIGTERM-and-exec-recovery-227B'


def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):
 assert type(row)is dict and set(row)=={'path','bytes','sha256'} and ref(row['path'])==row,'exact BYTE subject';return Path(row['path'])
def data(row):return json.loads(auth(row).read_bytes())
def read(path):return json.loads(Path(path).read_bytes())
def write(path,value):
 with Path(path).open('x')as f:f.write(json.dumps(value,indent=2)+'\n')
 return ref(Path(path))
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def inputs():
 b=read(REVIEW/'COMPLETE-COHORT-BINDINGS.json')
 assert ref(REVIEW/'COMPLETE-COHORT-BINDINGS.json')['sha256']=='915ba83a7f29f05a6a3e3fa48374591d05f24e960554780ff4cadb8b718b202b','exact reviewed cohort bindings'
 q=read(COHORT/'finalizer-window-clamp-correction-source-1/ROOT61-227-WINDOW-INPUT.TEMPLATE.NOT-AUTHORITY.json')
 for key in ['current_ledger','latest_free','current_observer_source','current_observer_source_review','current_observer_schema','current_observer_schema_review']:q[key]=b[key]
 for key in ['current_ledger','latest_free','offline_manifest','manifest','scratch_manifest_stage','composed_case_binding']:data(q[key])
 assert data(q['current_ledger'])['latest_accepted_free_boundary']==q['latest_free']
 return q,b


def actual_capability_checks(q,capability=None):
 """Original source/profile/manifest/loader/owner APIs; no native/guard/bind replay."""
 binder=module(BASE/'original227-contract-case-correction-source-1/bind_process227_collector.py','released227_source_validator')
 plan,facts,profile,diagnostic,owner=binder.source_check()
 manifest=data(q['offline_manifest']);receipt=read(manifest['staging']['overlay_manifest']['path']);stage=data(q['scratch_manifest_stage'])
 assert auth(q['manifest']).read_bytes()==auth(q['offline_manifest']).read_bytes()
 assert stage['source_manifest']==q['offline_manifest'] and stage['scratch_manifest']==q['manifest'] and stage['runtime_authority'] is None and stage['nonce'] is None
 diagnostic.load_manifest(q['offline_manifest']['path']);diagnostic.load_manifest(q['manifest']['path'])
 binder.check_collector(manifest,receipt,plan,facts,profile)
 supplement=binder.module('released227_executor_validator',plan['references']['executor_supplement'])
 supplement.check(manifest,receipt,binder.data(plan['references']['executor_contract']))
 owner._manifest_identity(q['manifest']['path'],q['manifest']['sha256'])
 owner._manifest_outside_writable_parent(q['manifest']['path'],stage['planned_attempt_parent'])
 if capability is not None:
  original=read(BASE/'ROOT-CASE-CAPABILITY.TEMPLATE.NOT-AUTHORITY.json')
  assert set(capability)==set(original),'released227 capability document keys only'
  assert capability['case_id']==manifest['case_id']==CASE
  for key in ['payload','artifacts','modules','profile']:assert capability[key]==manifest[key],'actual case '+key
  assert capability['compiled_producer_adoption']==original['compiled_producer_adoption'] and capability['compiled_producer_facts']==original['compiled_producer_facts']
  assert capability['executor_contract']==original['executor_contract'] and capability['actual_scratch_stage']==q['scratch_manifest_stage']
  assert capability['current_ledger']==q['current_ledger'] and capability['latest_free']==q['latest_free']
  assert capability['native_acceptance'] is False and capability['runtime_release'] is None
 return manifest,stage,plan,facts


def validate_generated_documents(q):
 authority=data(q['source_authority']);capability=data(q['case_capability']);stage_acceptance=data(q['stage_map_acceptance']);reservation=data(q['nonce_reservation'])
 original_authority=read(BASE/'ROOT-SOURCE-AUTHORITY.TEMPLATE.NOT-AUTHORITY.json')
 original_capability=read(BASE/'ROOT-CASE-CAPABILITY.TEMPLATE.NOT-AUTHORITY.json')
 historical_reservation=read(E/'m14-f02-current115-matching235-native-preparation-source-1/normal-entry-preclock-source-2/ROOT-ACTUAL-NONCE-RESERVATION.json')
 assert set(authority)==set(original_authority) and set(capability)==set(original_capability) and set(reservation)==set(historical_reservation),'released document schema keys'
 assert authority['author']==authority['authorized_by']=='/root' and authority['case_id']==CASE and authority['runtime_authority'] is None
 for key,qkey in [('actual_bound_manifest','offline_manifest'),('actual_scratch_manifest','manifest'),('current_observer','current_observer_source'),('current_observer_review','current_observer_source_review'),('current_ledger','current_ledger'),('latest_free','latest_free'),('case_capability','case_capability')]:assert authority[key]==q[qkey],'sourceauthority exact '+key
 assert authority['nonce']==reservation['nonce']==q['nonce'] and reservation['author']=='/root' and reservation['current_ledger']==q['current_ledger'] and reservation['maximum_invocations']==1 and reservation['runtime_authority'] is None
 stage=data(q['scratch_manifest_stage']);assert set(stage_acceptance)==set(stage)
 assert {k:v for k,v in stage_acceptance.items()if k!='status'}=={k:v for k,v in stage.items()if k!='status'},'Root stage acceptance preserves all actual fields'
 assert authority['independent_actual_stage'] is None and capability['independent_actual_stage_acceptance'] is None,'no invented independentactual stage'
 actual_capability_checks(q,capability)
 return True


def sealing_subjects():
 q,b=inputs();host=read(BASE.parent/'actual-host-bound-source-1/STATIC-NATIVE-BINDINGS.HOST-BOUND.NOT-RELEASED.json')
 result=dict(root61=q['current_ledger'],current_free=q['latest_free'],manifest=q['offline_manifest'],scratch_stage=q['scratch_manifest_stage'],collector_facts=host['compiled_collector_facts'],collector_profile=host['compiled_collector_caseprofile'],collector_adoption=host['compiled_collector_adoption'],original227_contract=ref(BASE/'original227-contract-case-correction-source-1/SOURCE-BOUND-NATIVE-CONTRACT.ORIGINAL227-ADDITIVE.json'),observer=q['current_observer_source'],observer_schema=q['current_observer_schema'],owner=host['owner_source'],evaluator=host['evaluator_source'],executor_supplement=host['executor_supplement'],finalizer=ref(FINALIZER),root_data_filler=ref(Path(__file__)))
 for p in sorted((COHORT/'cohort').glob('*.py')):result['source_template:'+p.name]=ref(p)
 return result


def runtime_subjects(entry,root_data_dir):
 """No runtime-config/dependency/review backrefs: those are separate reviewed DATA."""
 result=sealing_subjects();entry=Path(entry);root_data_dir=Path(root_data_dir)
 for name in ['prepare_startup_bindings.py','bind_startup_resource.py','run_startup_resource_once.py','capture_fresh_startup_resource.py','run_native_startup_capture.py','runtime_guard.py','root_once_startup_entry.py','STATIC-NATIVE-BINDINGS.NOT-RELEASED.json']:result['final_consumer:'+name]=ref(entry/name)
 for name in ['ROOT-SOURCE-AUTHORITY.CONDITIONAL.json','ROOT-CASE-CAPABILITY.CONDITIONAL.json','ROOT-STAGE-MAP-SOURCE-ACCEPTANCE.json','ROOT-NONCE-RESERVATION.SOURCE-ONLY.json','ROOT-FINAL-INPUT.SOURCE-ONLY.json']:result['source_data:'+name]=ref(root_data_dir/name)
 return result


def render(nonce,sealing_config,recorded_at,output):
 q,b=inputs();ledger=data(q['current_ledger'])
 assert re.fullmatch('[0-9a-f]{32}',nonce) and nonce not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']+ledger.get('reserved_unused_nonces',[]),'Root selected unused nonce only'
 assert re.fullmatch(r'2026-10-(?:28|29)T[0-9:.]+(?:Z|\+00:00)',recorded_at),'Root supplied actual record time required'
 record_epoch=datetime.datetime.fromisoformat(recorded_at.replace('Z','+00:00')).timestamp()
 assert data(q['latest_free'])['last_observed_clocks'][0]<=record_epoch<1793253600.0,'Root record time within remaining actual window'
 expected=sealing_subjects();configuration=data(sealing_config);assert configuration['operation']=='original227' and configuration['subjects']==expected,'exact SEALING subject map'
 q['operation_guard_configuration']=sealing_config
 producer=module(FINALIZER,'reviewed_finalizer_window_contract')
 producer.seal_new_operation_window(q,read(producer.HOST_STATIC)) # Real pure configure/current_cutoffs validator.
 manifest,stage,plan,facts=actual_capability_checks(q)
 output=Path(output);output.mkdir(mode=0o700)
 # Same released stage receipt keys, explicitly Root SOURCE adoption only. It is
 # not an independently issued actual fullarchive acceptance or runtime release.
 stage_acceptance=copy.deepcopy(stage);stage_acceptance['status']='ROOT_ACCEPTED_RETAINED_ORIGINAL227_STAGE_AND_MAP_SOURCE_ONLY'
 stage_ref=write(output/'ROOT-STAGE-MAP-SOURCE-ACCEPTANCE.json',stage_acceptance)
 cap=read(BASE/'ROOT-CASE-CAPABILITY.TEMPLATE.NOT-AUTHORITY.json')
 cap.update(author='/root',status='ROOT_ORIGINAL227_STAGED_CAPABILITY_CONDITIONAL_NOT_RUNTIME_RELEASE',current_ledger=q['current_ledger'],latest_free=q['latest_free'])
 # Independent actual-stage field remains honest: no independent acceptance is
 # invented by Root source adoption. Original fresh execution review is mandatory.
 assert cap['independent_actual_stage_acceptance'] is None
 actual_capability_checks(q,cap)
 capref=write(output/'ROOT-CASE-CAPABILITY.CONDITIONAL.json',cap)
 authority=read(BASE/'ROOT-SOURCE-AUTHORITY.TEMPLATE.NOT-AUTHORITY.json')
 authority.update(author='/root',authorized_by='/root',status='ROOT_ORIGINAL227_SOURCE_ADOPTION_CONDITIONAL_NOT_NATIVE_RELEASE',current_observer=q['current_observer_source'],current_observer_review=q['current_observer_source_review'],current_ledger=q['current_ledger'],latest_free=q['latest_free'],nonce=nonce,case_capability=capref,fixed_deadline='2026-10-29T06:00:00Z')
 authorityref=write(output/'ROOT-SOURCE-AUTHORITY.CONDITIONAL.json',authority)
 historical=read(E/'m14-f02-current115-matching235-native-preparation-source-1/normal-entry-preclock-source-2/ROOT-ACTUAL-NONCE-RESERVATION.json')
 reservation=copy.deepcopy(historical);reservation.update(nonce=nonce,status='RESERVED_UNUSED_ORIGINAL227_SOURCE_ONLY_NOT_RELEASED',recorded_at=recorded_at,current_ledger=q['current_ledger'])
 reservationref=write(output/'ROOT-NONCE-RESERVATION.SOURCE-ONLY.json',reservation)
 q.update(author='/root',Root_attests_exact_current_boundary=True,nonce=nonce,nonce_reservation=reservationref,source_authority=authorityref,case_capability=capref,stage_map_acceptance=stage_ref)
 validate_generated_documents(q)
 qref=write(output/'ROOT-FINAL-INPUT.SOURCE-ONLY.json',q)
 write(output/'SOURCE-DATA-RESULT.json',dict(scope=__doc__.splitlines()[0],status='ROOT_SOURCE_DATA_FILLED_REAL_RELEASED227_SCHEMAS_NO_RUNTIME_RELEASE',input=qref,sealing_subjects=expected,stage_map_scope='Root source adoption of real retained stage/map only; no independent actual fullarchive receipt fabricated',runtime_authority=None,next_argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(FINALIZER),'--seal-source-context','--root-inputs',qref['path'],'--root-inputs-sha256',qref['sha256']]))
 return q


def main():
 a=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);g=a.add_mutually_exclusive_group(required=True);g.add_argument('--sealing-subjects',action='store_true');g.add_argument('--runtime-subjects',type=Path);g.add_argument('--fill-source-data',action='store_true');a.add_argument('--root-data-dir',type=Path);a.add_argument('--nonce');a.add_argument('--sealing-config',type=Path);a.add_argument('--sealing-config-sha256');a.add_argument('--recorded-at');a.add_argument('--output-dir',type=Path);q=a.parse_args()
 if q.sealing_subjects:print(json.dumps(sealing_subjects(),indent=2));return
 if q.runtime_subjects:assert q.root_data_dir;print(json.dumps(runtime_subjects(q.runtime_subjects,q.root_data_dir),indent=2));return
 assert q.nonce and q.sealing_config and q.recorded_at and q.output_dir and ref(q.sealing_config)['sha256']==q.sealing_config_sha256
 result=render(q.nonce,ref(q.sealing_config),q.recorded_at,q.output_dir);print(json.dumps(dict(status='ROOT_SOURCE_DATA_ONLY_NOT_NATIVE_RELEASE',input=ref(q.output_dir/'ROOT-FINAL-INPUT.SOURCE-ONLY.json'),runtime_authority=None)))
if __name__=='__main__':main()
