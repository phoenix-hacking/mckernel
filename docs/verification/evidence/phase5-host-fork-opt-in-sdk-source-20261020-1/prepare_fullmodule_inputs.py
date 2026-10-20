"""Finite private CURRENT-v6 fullcrate SDK inputs; never current-main integration or execution."""
from pathlib import Path
import hashlib,json,re
N=Path(__file__).resolve().parent
SDK=Path('/home/holden/mckernel-work/host-preparation/current-parent-pin-sdk-preparation-20261019-1')
PLAN_SHA='20b5d6f908649e7d45287ae3acaf054856d5305ca53b474e589d5389bbf2c7d6'
NONCE='3e1cf8539a774a9389e19f471828676b'
ROOT=Path('/home/holden/mckernel-work/scratch');C=ROOT/('nsd-c-'+NONCE);I=ROOT/('nsd-i-'+NONCE);E=ROOT/('nsd-o-'+NONCE)
PREP='current-v6-host-fork-opt-in-sdk-20261020-1.json'
def digest(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 b=p.read_bytes();return dict(path=str(p),sha256=digest(b),bytes=len(b))
def checked(r):
 b=Path(r['path']).read_bytes();assert len(b)==r['bytes'] and digest(b)==r['sha256'];return b
def write(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b)
 assert p.read_bytes()==b

def put(p,x):write(p,(json.dumps(x,sort_keys=True,indent=2)+'\n').encode())
def main():
 planraw=(N/'SOURCE-PLAN.json').read_bytes();assert digest(planraw)==PLAN_SHA;plan=json.loads(planraw)
 assert plan['source_files']==66 and len(plan['rows'])==66 and plan['route_overlay_files']==15
 assert not any(p.exists() for p in (N/'capsule',N/'source-modules',N/'prepared-inputs',C,I,E,N/'request.json'))
 for r in plan['rows']:write(N/'source-modules'/r['relative'],checked(r['source']))
 oldindex=json.loads((SDK/'CAPSULE-AND-MATERIALIZATION-INDEX.json').read_bytes());oldq=json.loads((SDK/'request.json').read_bytes());oldprep=json.loads(checked(oldindex['preparation']));oldrows=json.loads(checked(oldindex['materialization_files']));oldmap=json.loads(checked(oldindex['source_map']))
 assert len(oldmap)==11 and len(oldrows)==75
 def bind(x):
  if isinstance(x,str):return x.replace(oldq['candidate_root'],str(C)).replace(oldq['input_root'],str(I)).replace(oldq['owner_evidence_root'],str(E))
  if isinstance(x,list):return [bind(v) for v in x]
  if isinstance(x,dict):return {k:bind(v) for k,v in x.items()}
  return x
 prep=bind(oldprep);previous={r['path']:r for r in prep['closure']};closure=[]
 for r in plan['rows']:
  name=r['relative'];row=dict(previous.get(name,{}));row.update(path=name,origin=str(C/'modules'/name),sha256=r['source']['sha256'],bytes=r['source']['bytes'],parent_source_sha256=previous.get(name,{}).get('sha256'),baseline_sha256=previous.get(name,{}).get('baseline_sha256'),reviewed_replacement=(r['source']['sha256']!=previous.get(name,{}).get('baseline_sha256')),compile_target_source_origin=r['origin']);closure.append(row)
 prep.update(task_id='current-v6-fork-adoption-sdk-20261020-1',closure=closure,closure_files=66,closure_bytes=plan['source_bytes'],source_candidate_sha=plan['source_identity'],parent_source_candidate_sha=oldprep['source_candidate_sha'],source_commit_binding=dict(commit=None,pending=False,source_identity=plan['source_identity'],scope=plan['source_identity_scope']),source_review=dict(route=plan['route_receipt'],fullcrate='CURRENT_V6_ROUTE_REVIEW_PENDING'),only_delta=dict(route_files=15,current_main_changed=False,held_sources_used=False),source_copy_method='66 individually pinned accepted HOST66 snapshots plus explicit cfg/build mode; no held66 or objects',source_closure_reused_without_recopy_or_rehash=False,execution_authorized=False,execution_demonstrated=False,production_acceptance=False,acceptance=False,blocker='Actual source materialization/publication/exact heavy release pending',excluded_working_tree='Only exact SOURCE-PLAN opt-in66 closure is selected; no current-main mutation',provenance_closure_sha256=plan['source_identity'])
 mode=plan['host_fork_adoption_opt_in'];assert type(mode) is bool
 prep['host_fork_adoption_opt_in']=mode
 argv=prep['proposed_external_command'];assert not any(x.startswith('MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN=') for x in argv)
 argv.insert(argv.index('--jobserver-style=pipe'),'MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN='+('1' if mode else '0'))
 pp=N/'capsule/docs/verification/evidence'/PREP;put(pp,prep);ph=ref(pp)['sha256'];mapping={}
 for name,h in oldmap.items():
  b=(SDK/'capsule'/name).read_bytes();assert digest(b)==h
  if name.endswith('native_running_external_modules_offline.py'):
   text=checked(plan['driver_template']).decode()
   text=re.sub(r'^PREPARATION_SHA256 = .*$', 'PREPARATION_SHA256 = '+repr(ph), text, flags=re.M)
   # Current-v6 template already pins exact source identity, count and bytes.
   replacements={r['path']:r['sha256'] for r in closure if r['reviewed_replacement']}
   text,n=re.subn(r'^REPLACEMENTS = .*$',lambda m:'REPLACEMENTS = '+repr(replacements),text,flags=re.M);assert n==1
   b=text.encode()
  elif name.endswith('native_running_external_modules_owner.py'):
   text=b.decode().replace(oldprep['source_candidate_sha'],plan['source_identity']).replace(oldindex['preparation']['sha256'],ph).replace('current-parent-pin-sdk-preparation-20261019-1.json',PREP).replace('native-current-parent-pin-sdk-external-modules','native-current-v6-host-fork-opt-in-external-modules').replace("len(prep['closure']) == 60","len(prep['closure']) == 66");b=text.encode()
  write(N/'capsule'/name,b);mapping[name]=digest(b)
 put(N/'source-sha256.json',mapping)
 q=dict(oldq);q.update(nonce=NONCE,candidate_root=str(C),input_root=str(I),owner_evidence_root=str(E),lease_path=str(ROOT/'native-current-v6-host-fork-opt-in-external-modules.lease.json'),common_exclusion_path=str(ROOT/'native-current-v6-host-fork-opt-in-external-modules-operational-exclusion.json'),request_path=str(N/'request.json'),candidate_identity=None,input_identity=None)
 driver=N/'capsule/scripts/native_running_external_modules_offline.py';owner=N/'capsule/scripts/native_running_external_modules_owner.py';q['driver']={k:v for k,v in ref(driver).items() if k!='bytes'};q['preparation']={k:v for k,v in ref(pp).items() if k!='bytes'};put(N/'request-TEMPLATE.json',q)
 rows=[dict(destination=str(C/'modules'/r['relative']),source=ref(N/'source-modules'/r['relative'])) for r in plan['rows']]
 for row in oldrows[60:]:
  destination=str(I/Path(row['destination']).name)
  if Path(destination).name=='preparation.json':source=pp
  else:source=N/'prepared-inputs'/Path(destination).name;write(source,checked(row['source']))
  rows.append(dict(destination=destination,source=ref(source)))
 assert len(rows)==81;put(N/'materialization-files.json',rows)
 index=dict(oldindex);index.update(nonce=NONCE,driver=ref(driver),owner=ref(owner),preparation=ref(pp),request_template=ref(N/'request-TEMPLATE.json'),materialization_files=ref(N/'materialization-files.json'),source_map=ref(N/'source-sha256.json'),materialization_copy_rows=81,owner_function_class_ast_equal=False,owner_affected_function='validate_request: exactclosurecount60to66only',proof=ref(N/'prepared-inputs/make-pipe-proof.json'),status='PRIVATE_FULLCRATE_COMPILE_TARGET_ONLY_NO_EXECUTION_AUTHORITY');put(N/'CAPSULE-AND-MATERIALIZATION-INDEX.json',index)
 print(json.dumps(dict(status='PREPARED_PRIVATE_HELD_FULLCRATE_INPUTS_ONLY',source_files=66,copy_rows=81,engine_catalog=11,source_bytes=plan['source_bytes'],current_main_mutations=0,compiler_calls=0)))
if __name__=='__main__':main()
