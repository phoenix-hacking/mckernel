"""Finite source6 DATA binding; all production function bodies retained.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import argparse,ast,hashlib,json,os,stat
T=Path(__file__).resolve().parent;C=T.parent;A=C/'pinned-launcher-attempt-1';S=Path('/home/holden/mckernel-work/host-preparation/p-m06-current-build-terminal-preparation-20261022-1/bound-current-controller-source-6');O=T/'bound-current-controller-source-1'
p=argparse.ArgumentParser();p.add_argument('--controller-review',required=True);p.add_argument('--controller-review-sha256',required=True);args=p.parse_args()
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def load(p):return json.loads(Path(p).read_bytes())
def save(p,x):
 b=x if isinstance(x,str)else json.dumps(x,sort_keys=True,indent=2)+'\n'
 with p.open('x')as f:f.write(b)
def global_value(s,name,value):
 n=next(n for n in ast.parse(s).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id==name for t in n.targets));lines=s.splitlines(True);lines[n.lineno-1:n.end_lineno]=[name+' = '+value+'\n'];return ''.join(lines)
def identity(p):
 p=Path(p);s=p.lstat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
def bodies(s):return{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
x=load(T/'ACTUAL-CLOSED-LAUNCHER-RECORDS.json');proofref=ref(T/'CURRENT-CONTROLLER-PROOF.json');proof=load(proofref['path']);reviewref=ref(args.controller_review);assert reviewref['sha256']==args.controller_review_sha256;review=load(reviewref['path']);assert review['accepted_proof']==proofref and review['decision']=='PASS_ACTUAL_M06_SINGLE_CHILD_CONTROLLER_AND_SEVEN_DOCKER_CLIENTS_SOURCE_ONLY'and review['findings']==[]and review['implementation_ownership']is False
roles=proof['roles'];request=load(roles['request']['path']);owner=load(roles['owner']['path']);driver=load(roles['driver']['path']);oldcase=load(S/'LAUNCHER-CASE-STATIC.json');plan=load(request['launcher_plan']['path']);refs=dict(roles);contractref=ref(T/'current_controller_contract.py');refs.update(controller_proof=proofref,controller_review=reviewref,controller_contract=contractref)
for k in ('driver_path','provenance_path','host_owner_path','source_manifest','toolchain_manifest','gitlink_manifest'):
 if k in ('source_manifest','toolchain_manifest','gitlink_manifest'):refs[k]=oldcase['finite_roles'][k];assert refs[k]['path']==request[k]and refs[k]['sha256']==request[k+'_sha256']
 else:refs[k]=ref(request[k])
refs.update(image_owner=roles['owner_source'],launcher_plan=request['launcher_plan'],materialization=oldcase['finite_roles']['materialization'])
for k in ('base_driver','original_source','source_override','reviewed_preimage','source_patch','source_review'):refs['launcher_'+k]=plan[k]
for k,v in driver['artifacts'].items():refs['artifact:'+k]=ref(Path(request['work_root'])/str(Path(v['path']).relative_to('/work')))
for k in driver['artifact_copies']:refs['evidence_artifact:'+k]=ref(A/'owner-work/evidence/artifacts'/k)
for q in (A/'owner-work/output/build/executer/user/mcexec',A/'owner-work/output/build/executer/user/rust/mcexec_helpers.o',A/'owner-evidence/attempt/container.log'):refs['actual:'+q.name]=ref(q)
for i,row in enumerate(proof['controller_client_ledger']['docker_clients']):
 for k in ('status','stdout','stderr'):refs['docker:%d:%s'%(i,k)]=row[k]
ns=A.lstat();nsbind=dict(device=ns.st_dev,inode=ns.st_ino,uid=ns.st_uid,gid=ns.st_gid,mode=ns.st_mode);ancestry=[identity(p)for p in reversed((A,*A.parents))]
case=dict(schema=oldcase['schema'],controller_proof=proofref,controller_review=reviewref,controller_client_ledger=proof['controller_client_ledger'],artifact_acceptance=roles['artifact_review'],request=roles['request'],target=proof['target'],source_identity=x['source_identity'],finite_roles=refs,finite_role_count=len(refs),finite_unique_paths=sorted({r['path']for r in refs.values()}),retained_ownership=x['retained_ownership'],namespace=str(A),namespace_binding=nsbind,namespace_ancestry=ancestry,successful_artifacts_required=True,execution_authorized=False,current_live_postjoin=None,guard_result=None,physical_release=False,cleanup_release=None,runtime_release=None)
O.mkdir(mode=0o700);save(O/'LAUNCHER-CASE-STATIC.json',case);caseref=ref(O/'LAUNCHER-CASE-STATIC.json');engine=(S/'cleanup_launcher.py').read_text();oldowner='4c4d4efc2feb6cd744cd0eb6da047bf1deef67eb8b00ea6c67ed1dcc305710b1';newowner=roles['owner_source']['sha256'];assert newowner=='c9eb78a4c1113f6bee6b809fc07d215978b2914f6edefe73d85757e32dea2f42'
# Exact existing owner-code pin in current8mount dispatch; no branch/body algorithm changes.
assert engine.count("SOURCE_REFS['image_owner']['sha256']=='"+oldowner+"'")==1;engine=engine.replace("SOURCE_REFS['image_owner']['sha256']=='"+oldowner+"'","SOURCE_REFS['image_owner']['sha256']=='"+newowner+"'")
values=dict(SOURCE_REFS=repr(refs),CURRENT_TYPED_REQUEST=repr(case['source_identity']),CURRENT_LAUNCHER_PLAN=repr(request['launcher_plan']),PUBLISHED_SCRIPT=repr('docs/verification/evidence/'+str(O/'cleanup_launcher.py').split('/host-preparation/',1)[1]),NAMESPACE='Path('+repr(str(A))+')',NAMESPACE_BINDING=repr(nsbind),NAMESPACE_ANCESTRY=repr(ancestry),PREFIX=repr('v3-launcher-current-controller-20261023-1'),ATTEMPT='Path('+repr(request['common_exclusion_path'])+')',REQUEST='Path('+repr(roles['request']['path'])+')',REQUEST_SHA=repr(roles['request']['sha256']),LEASE='Path('+repr(request['lease_path'])+')',OUTPUT='Path('+repr(request['work_root'])+')',EVIDENCE='Path('+repr(request['owner_evidence_root'])+')',KNOWN_TARGET=repr({k:v for k,v in proof['target'].items()if k!='image_id'}),IMAGE_CANDIDATE=repr(request['candidate_sha']),CURRENT_GUARD_CAPTURE='Path('+repr(owner['attempt_root'])+')',PASS_LOG_CHANNELS=repr({'status.json':x['log_channels']['status'],'stdout':x['log_channels']['stdout'],'stderr':x['log_channels']['stderr']}),CONTROLLER_CONTRACT_REF=repr(contractref),CONTROLLER_PROOF_REF=repr(proofref))
for k,v in values.items():engine=global_value(engine,k,v)
expected=(S/'cleanup_launcher.py').read_text().replace(oldowner,newowner);assert bodies(engine)==bodies(expected);save(O/'cleanup_launcher.py',engine);engineref=ref(O/'cleanup_launcher.py')
nonce='v3-launcher-controller-observation-20261023-1';obs=(S/'observe_current_launcher_retirement.py').read_text()
values=dict(FAILURE_CASE='Path('+repr(caseref['path'])+')',FAILURE_CASE_SHA=repr(caseref['sha256']),PREP='Path('+repr(str(O))+')',CASE='Path('+repr(str(A))+')',CAPTURE='Path('+repr(owner['attempt_root'])+')',SOURCE='Path('+repr(engineref['path'])+')',SOURCE_SHA=repr(engineref['sha256']),RETIREMENT='Path('+repr(proofref['path'])+')',RETIREMENT_SHA=repr(proofref['sha256']),NONCE=repr(nonce),BOOT=repr(owner['shared_heavy_operation']['record']['boot_id']),PIDS=repr(tuple([proof['target']['owner_pid']]+[r['pid']for r in proof['controller_client_ledger']['docker_clients']])),PENDING_BINDINGS='()',CURRENT_EXPECTED_SOURCE=repr(case['source_identity']),CONTROLLER_CONTRACT_REF=repr(contractref))
for k,v in values.items():obs=global_value(obs,k,v)
assert bodies(obs)==bodies((S/'observe_current_launcher_retirement.py').read_text());save(O/'observe_current_launcher_retirement.py',obs);obsref=ref(O/'observe_current_launcher_retirement.py')
for name,values in [('check_launcher_fresh_preflight.py',dict(SOURCE='Path('+repr(engineref['path'])+')',SOURCE_SHA=repr(engineref['sha256']))),('postjoin_launcher.py',dict(ENGINE='Path('+repr(engineref['path'])+')',ENGINE_SHA=repr(engineref['sha256']),OBSERVER='Path('+repr(obsref['path'])+')',OBSERVER_SHA=repr(obsref['sha256']))),('readback_observer.py',dict(OUTPUT='Path('+repr(str(O/('root-observation-'+nonce)))+')',NONCE=repr(nonce)))]:
 text=(S/name).read_text()
 for k,v in values.items():text=global_value(text,k,v)
 assert bodies(text)==bodies((S/name).read_text());save(O/name,text)
summaryref=ref(O/'readback_observer.py')
for name in ('read_original_five_metadata.py','export_raw_five.py'):
 text=global_value((S/name).read_text(),'SUMMARY_SHA',repr(summaryref['sha256']))
 if name=='export_raw_five.py':text=global_value(text,'OUTPUT','Path('+repr(str(O/('root-observation-'+nonce)))+')')
 assert bodies(text)==bodies((S/name).read_text());save(O/name,text)
for name in ('capture_first_four.py','capture_critical_two.py'):save(O/name,(S/name).read_text())
for q in O.glob('*.py'):ast.parse(q.read_bytes())
save(O/'SOURCE-PINS.json',dict(status='ACTUAL_CURRENT_CONTROLLER_SOURCE6_DATA_COHORT_NO_EXECUTION_AUTHORITY',files={q.name:ref(q)for q in O.iterdir()if q.is_file()},contract=contractref,controller_proof=proofref,controller_review=reviewref,previous_source6=str(S),function_bodies='All functions/classes byteAST unchanged except exact currentowner SHA literal in image_layout dispatch;8mount algorithm unchanged.'))
print(json.dumps(ref(O/'SOURCE-PINS.json'),sort_keys=True))
