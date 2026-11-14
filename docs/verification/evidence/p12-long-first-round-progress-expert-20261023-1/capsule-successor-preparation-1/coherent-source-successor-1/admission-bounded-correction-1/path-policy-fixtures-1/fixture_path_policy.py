"""Functional OS actual selected query predicate regression; no security testing.
Controlled path observations only, derived from genuine retained query/physical refs. Never fresh admission.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual_corrected_query',D/'read_only_LONG_HOST_admission.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
c=json.loads((D/'QUERY-INPUTS.json').read_bytes())
physical=Path(c['physical']['path']);raw=physical.read_bytes();assert hashlib.sha256(raw).hexdigest()==c['physical']['sha256'];actual=json.loads(raw)
assert actual['current_live_postjoin']['state']=='CANCELLED_LONG_POSITIVELY_RETIRED' and actual['current_live_postjoin']['nonce']==c['prior_failed_nonce']
prior=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/final-LONG-execution-preparation-1/bounded-correction-1/final-execution-assembly-1/post-M14-fresh-admission-preparation-1/expired-release-successor-1/serialized-release-successor-2/actual-root-observer-capture-1/stdout')
praw=prior.read_bytes();p=json.loads(praw);assert p['query_status']=='PASS_FRESH_READ_ONLY_P12_LONG_ADMISSION' and p['closed_capture']['returncode']==0
parent=Path(c['operation']['HOST_parent']);nonce=c['operation']['nonce'];paths=[c['operation']['capture_directory'],str(parent.with_name(parent.name+'.owner-'+nonce)),str(parent/('attempt-'+nonce)),c['operation']['future_release_path'],c['operation']['future_request_path']]
f={'physical':actual,'retained_previous_owner_evidence':{p:True for p in c['retained_previous_owner_evidence_paths']},'output_paths_exist':{p:False for p in paths}}
q.validate_output_path_policy(f,c);checks=[{'name':'genuine591c_retired_old_owner_evidence_present_new_paths_absent','status':'ACCEPTED_PATH_PREDICATE_ONLY'}]
def reject(label,facts,config):
 try:q.validate_output_path_policy(facts,config)
 except RuntimeError as e:checks.append({'name':label,'status':'REJECTED','error':str(e)})
 else:raise AssertionError('accepted invalid '+label)
for path in paths:
 mutant=copy.deepcopy(f);mutant['output_paths_exist'][path]=True;reject('fresh_collision:'+path,mutant,c)
mutant=copy.deepcopy(f);mutant['retained_previous_owner_evidence']={};reject('historical_policy_missing_observation',mutant,c)
mutant=copy.deepcopy(f);mutant['retained_previous_owner_evidence'][c['retained_previous_owner_evidence_paths'][0]]=False;reject('historical_evidence_absent',mutant,c)
mutant=copy.deepcopy(f);mutant['output_paths_exist'][c['retained_previous_owner_evidence_paths'][0]]=True;reject('historical_wrongly_classified_as_fresh',mutant,c)
changed=copy.deepcopy(c);changed['retained_previous_owner_evidence_paths']=[];reject('historical_policy_removed',f,changed)
changed=copy.deepcopy(c);changed['retained_previous_owner_retirement_authority']['sha256']='0'*64;reject('historical_retirement_pin_changed',f,changed)
mutant=copy.deepcopy(f);mutant['output_paths_exist'].pop(paths[0]);reject('fresh_path_inventory_omitted',mutant,c)
assert f['output_paths_exist']=={p:False for p in paths}
r={'scope':__doc__,'status':'PASS_ACTUAL_SELECTED_QUERY_PATH_PREDICATE_REGRESSIONS_ONLY','checks':checks,'selected_source_sha256':hashlib.sha256((D/'read_only_LONG_HOST_admission.py').read_bytes()).hexdigest(),'genuine_prior_query_capture':{'path':str(prior),'sha256':hashlib.sha256(praw).hexdigest()},'genuine_physical':c['physical'],'input_derivative':'Only path presence dictionary controlled; actual root observation capture/591c retained as authority, no fresh collect/PROC/Docker call or full admission claimed.','root':0,'Docker':0,'PROC_queries':0,'owner_or_lease_mutations':0,'fresh_admission':False,'native_acceptance':False}
with (D/'ACTUAL-PATH-PREDICATE-RESULT.json').open('x') as out:json.dump(r,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(r))
