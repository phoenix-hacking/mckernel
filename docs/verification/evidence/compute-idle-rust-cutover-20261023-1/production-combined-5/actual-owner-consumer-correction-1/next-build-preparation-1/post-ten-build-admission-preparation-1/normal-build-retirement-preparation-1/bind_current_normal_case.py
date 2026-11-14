"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source/metadata binding only. No cleanup/observer/query/workload invocation."""
from pathlib import Path
import ast,hashlib,json
D=Path(__file__).resolve().parent
BASE=D.parents[1]
OLD=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/matched-image-terminal-preparation-1/bound-matched-image-terminal-source-2')
P=D/'bound-current-normal-image-source-1'
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def row(p,sha,n):return dict(path=str(p),sha256=sha,bytes=n)
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
def assign(text,name,expression):
 n=next(n for n in ast.parse(text).body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name)
 lines=text.splitlines(keepends=True);lines[n.lineno-1:n.end_lineno]=[name+' = '+expression+'\n'];return ''.join(lines)
def function(text,name,replacement):
 n=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name)
 lines=text.splitlines(keepends=True);lines[n.lineno-1:n.end_lineno]=[replacement.rstrip()+'\n'];return ''.join(lines)
capture=BASE/'post-ten-build-admission-preparation-1/actual-build-owner-capture-1'
owner=read(capture/'stdout');closed=read(capture/'status.json')
request=read(BASE/'image-request.PREPARED.json');work=Path(request['work_root']);evidence=Path(request['owner_evidence_root'])
driver=read(Path(request['evidence_root'])/'receipt.json')
inspect_ref=ref(D/'actual-readonly-terminal-inspect-1/stdout')
assert inspect_ref['sha256']=='42cb8155240030114cfdd5f48ff327064bfd7b1b44fca649455ea3c411476aa5'
inspection=read(inspect_ref['path']);assert len(inspection)==1;inspection=inspection[0]
artifact=Path('/home/holden/mckernel/docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-5/actual-owner-consumer-correction-1/next-build-preparation-1/post-ten-build-admission-preparation-1/actual-default-link-retention-1/INDEPENDENT-ACTUAL-M14-DEFAULT-LINK-ACCEPTANCE.json')
assert ref(artifact)['sha256']=='38694775a6d61aaf761683defd37401347f73aec391b1f464407c8c2f77ba0dc'
accepted=read(artifact)
assert accepted['status']=='PASS_ACTUAL_M14_DEFAULT_LINK_ONLY'
assert closed['pid']==3725755 and closed['proc_start_ticks']=='55985185'
assert owner['owner_nonce']=='c90a9cee3da242fa90366c447a25a081' and inspection['Id']==owner['container_id']
assert not P.exists() or not any(P.iterdir());P.mkdir(mode=0o700,exist_ok=True)
target={k:owner[k] for k in ('container_id','container_name','owner_nonce')}
target.update(owner_pid=closed['pid'],owner_starttime=closed['proc_start_ticks'],exit_code=owner['exit_code'],image_id=inspection['Image'])
source_keys=('candidate_identity_scope','candidate_sha','materialization_sha256','source_derivative_sha256','source_identity','source_root')
typed={k:request[k] for k in source_keys}
roles={'request':ref(BASE/'image-request.PREPARED.json'),'owner_receipt':ref(evidence/'owner-receipt.json'),'driver_receipt':ref(Path(request['evidence_root'])/'receipt.json'),'guard_result':ref(capture/'status.json'),'outer_status':ref(capture/'status.json'),'outer_stdout':ref(capture/'stdout'),'outer_stderr':ref(capture/'stderr'),'terminal_inspection':inspect_ref,'image_owner':ref(BASE/'native_rust_exact_mckernel_image_container_owner.py'),'artifact_acceptance':ref(artifact),'materialization':ref(Path(request['source_root']).parent/'MATERIALIZATION-RESULT.json')}
for key in ('driver_path','provenance_path','host_owner_path','source_manifest','toolchain_manifest','gitlink_manifest'):
 sha_key=key.replace('_path','')+'_sha256' if key.endswith('_path') else key+'_sha256'
 roles[key]=row(request[key],request[sha_key],Path(request[key]).stat().st_size)
def host(p):return work/Path(p).relative_to('/work')
for group in ('artifacts','evidence_artifacts'):
 for key,v in driver[group].items():roles[group+':'+key]=row(host(v['path']),v['sha256'],v['size'])
for key,v in driver['inventory'].items():roles['driver_inventory:'+key]=row(Path(request['evidence_root'])/key,v['sha256'],v['size'])
roles['container_log']=ref(evidence/'attempt/container.log')
clients=[];log=None
for i,path in enumerate(sorted((evidence/'attempt').glob('command-*/status.json'))):
 status=read(path);assert status['state']=='exited' and status['exit_code']==0 and not status.get('client_retirement_unproven')
 client=dict(pid=status['pid'],status=ref(path),stdout=ref(path.parent/'stdout'),stderr=ref(path.parent/'stderr'));clients.append(client)
 for name in ('status','stdout','stderr'):roles['client:%d:%s'%(i,name)]=client[name]
 if 'logs' in status['argv']:log={'status.json':client['status'],'stdout':client['stdout'],'stderr':client['stderr']}
assert len(clients)==7 and log and log['stderr']['bytes']==0
write(P/'CURRENT-LIVE-POSTJOIN.HOLD.json',accepted['current_live_postjoin'])
roles['guard_postjoin']=ref(P/'CURRENT-LIVE-POSTJOIN.HOLD.json')
namespace=evidence.parent
ancestry=[]
for path in reversed((namespace,*namespace.parents)):
 s=path.lstat();ancestry.append(dict(path=str(path),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=s.st_mode))
ns={k:v for k,v in ancestry[-1].items() if k!='path'}
retirement={'schema':'mckernel.m14.normal-image.closed-retained-build-authority.v1','status':'HOLD_RETAINED_BUILD_OWNERSHIP','source_identity':typed,'target':target,'owner_receipt':roles['owner_receipt'],'guard_result':roles['guard_result'],'outer_status':roles['outer_status'],'terminal_fresh_inspect':inspect_ref,'artifact_acceptance':roles['artifact_acceptance'],'current_live_postjoin':roles['guard_postjoin'],'shared_record_from_actual_owner':owner['shared_heavy_operation'],'physical_release':False,'cleanup_authorized':False}
write(P/'CURRENT-RETAINED-BUILD-AUTHORITY.HOLD.json',retirement)
roles['retained_review']=ref(P/'CURRENT-RETAINED-BUILD-AUTHORITY.HOLD.json')
case={'schema':'mckernel.m14.current-normal-image.finite-terminal-case.v1','status':'ACTUAL_CLOSED_IMAGE_INPUTS_NO_PHYSICAL_RELEASE','target':target,'request':roles['request'],'source_identity':typed,'namespace':str(namespace),'namespace_binding':ns,'namespace_ancestry':ancestry,'guard_capture':str(evidence/'attempt'),'current_live_postjoin':roles['guard_postjoin'],'artifact_acceptance':roles['artifact_acceptance'],'finite_roles':roles,'finite_role_count':len(roles),'finite_unique_paths':sorted({x['path'] for x in roles.values()}),'finite_unique_path_count':len({x['path'] for x in roles.values()}),'successful_artifacts_required':True,'execution_authorized':False,'physical_release':False,'cleanup_release':None,'cleanup_result':None,'client_ledger':clients}
write(P/'PASS-CASE-STATIC.json',case)
engine=(OLD/'cleanup_pass_image.py').read_text()
values={'SOURCE_REFS':repr(roles),'CURRENT_TYPED_REQUEST':repr(typed),'PUBLISHED_SCRIPT':repr('docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-5/actual-owner-consumer-correction-1/next-build-preparation-1/post-ten-build-admission-preparation-1/normal-build-retirement-preparation-1/bound-current-normal-image-source-1/cleanup_pass_image.py'),'NAMESPACE':'Path('+repr(str(namespace))+')','NAMESPACE_ANCESTRY':repr(ancestry),'NAMESPACE_BINDING':repr(ns),'PREFIX':repr('m14-normal-image-terminal-20261023-1'),'ATTEMPT':'Path('+repr(request['common_exclusion_path'])+')','REQUEST':'Path('+repr(str(BASE/'image-request.PREPARED.json'))+')','LEASE':'Path('+repr(request['lease_path'])+')','OUTPUT':'Path('+repr(str(work))+')','EVIDENCE':'Path('+repr(str(evidence))+')','KNOWN_TARGET':repr({k:v for k,v in target.items() if k!='image_id'}),'REQUEST_SHA':repr(roles['request']['sha256']),'IMAGE_CANDIDATE':repr(request['candidate_sha']),'PASS_LOG_CHANNELS':repr(log)}
for key,value in values.items():engine=assign(engine,key,value)
engine=engine.replace("guard_capture = ROOT / 'native-rust-phase5-current-optin-image-guard-d18ea24c04e0435cbd8f673e253dc59d'","guard_capture = Path("+repr(str(evidence/'attempt'))+")")
old="""if proof_key == 'guard_proof' and (ROOT_TERMINAL.name != 'guard-result.json' or ROOT_TERMINAL.parent.parent != ROOT or
            ROOT_TERMINAL.parent.name != 'native-rust-phase5-current-optin-image-guard-d18ea24c04e0435cbd8f673e253dc59d'):"""
new="if proof_key == 'guard_proof' and ROOT_TERMINAL != Path("+repr(str(capture/'status.json'))+"):"
assert old in engine;engine=engine.replace(old,new)
engine=function(engine,'image_receipt_binding',"""
def image_receipt_binding(receipt, guard, target, item, receipt_sha):
    # Source-authority successor: this actual owner was directly captured,
    # rather than wrapped by the historical opt-in guard. Require its full
    # actual closed direct-capture proof, never invent a guard-result PASS.
    image_owner_receipt_binding(receipt,item,receipt_sha)
    status_ref=SOURCE_REFS['outer_status'];out_ref=SOURCE_REFS['outer_stdout']
    status_raw=read_bounded(Path(status_ref['path']));out_raw=read_bounded(Path(out_ref['path']))
    if (digest(status_raw)!=status_ref['sha256'] or digest(out_raw)!=out_ref['sha256'] or
            guard!=parse(status_raw) or parse(out_raw)!=receipt or
            guard.get('status')!='PASS' or guard.get('returncode')!=0 or
            guard.get('direct_child_joined') is not True or
            guard.get('process_group_absent') is not True or guard.get('streams_closed') is not True or
            guard.get('pid')!=target['owner_pid'] or str(guard.get('proc_start_ticks'))!=target['owner_starttime'] or
            guard.get('stdout',{}).get('sha256')!=out_ref['sha256'] or guard.get('stderr',{}).get('bytes')!=0 or
            receipt.get('exit_code')!=target['exit_code'] or target['exit_code']!=0 or
            any(receipt.get(k)!=target[k] for k in ('container_id','container_name','owner_nonce'))):
        raise Refusal('current-direct-image-owner-closed-capture-binding')
""")
engine=engine.replace("receipt.get('status')!='PASS_SOURCE_MATERIALIZATION_ONLY' or receipt.get('source')!=request['source_root']","receipt.get('status')!='PASS_COHERENT_LATEST_FIVE_POSTIMAGE_SOURCE_MATERIALIZATION_ONLY' or receipt.get('source_root')!=request['source_root']")
ast.parse(engine);(P/'cleanup_pass_image.py').write_text(engine)
observer=(OLD/'observe_current_pass_image_retirement.py').read_text()
ovalues={'FAILURE_CASE':'Path('+repr(str(P/'PASS-CASE-STATIC.json'))+')','FAILURE_CASE_SHA':repr(ref(P/'PASS-CASE-STATIC.json')['sha256']),'PREP':'Path('+repr(str(P))+')','CASE':'Path('+repr(str(namespace))+')','CAPTURE':'Path('+repr(str(evidence/'attempt'))+')','SOURCE':'Path('+repr(str(P/'cleanup_pass_image.py'))+')','SOURCE_SHA':repr(ref(P/'cleanup_pass_image.py')['sha256']),'RETIREMENT':'Path('+repr(str(P/'CURRENT-RETAINED-BUILD-AUTHORITY.HOLD.json'))+')','RETIREMENT_SHA':repr(ref(P/'CURRENT-RETAINED-BUILD-AUTHORITY.HOLD.json')['sha256']),'NONCE':repr('m14-normal-image-terminal-observation-20261023-1'),'BOOT':repr(owner['shared_heavy_operation']['record']['boot_id']),'PIDS':repr(tuple(c['pid'] for c in clients)),'TERMINAL_INSPECTION_SHA':repr(inspect_ref['sha256']),'CURRENT_EXPECTED_SOURCE':repr(typed)}
for key,value in ovalues.items():observer=assign(observer,key,value)
observer=function(observer,'current_pass_prerequisites',"""
def current_pass_prerequisites(retirement,case,root_join,artifact):
    # Genuine current M14 build/closed direct-capture authority. This record
    # explicitly retains physical HOLD; root mutex, publisher census and full
    # record identities are independently acquired by the unchanged observer.
    need(retirement['schema']=='mckernel.m14.normal-image.closed-retained-build-authority.v1' and
         retirement['status']=='HOLD_RETAINED_BUILD_OWNERSHIP' and retirement['physical_release'] is False and
         retirement['cleanup_authorized'] is False and case['execution_authorized'] is False and
         case['successful_artifacts_required'] is True,'current retained normal-image case required')
    need(retirement['target']==case['target'] and case['source_identity']==CURRENT_EXPECTED_SOURCE and
         retirement['source_identity']==CURRENT_EXPECTED_SOURCE,'exact current target/source authority')
    for key in ('owner_receipt','guard_result','outer_status','artifact_acceptance'):
        need(retirement[key]==case['finite_roles'][key],'exact current closed source role:'+key)
    need(retirement['terminal_fresh_inspect']==case['finite_roles']['terminal_inspection'] and
         retirement['current_live_postjoin']==case['current_live_postjoin'],'exact current retained observation refs')
    need(artifact['schema']=='m14-actual-production-default-link-independent-root-record-v1' and
         artifact['status']=='PASS_ACTUAL_M14_DEFAULT_LINK_ONLY' and artifact['independent_reviewer'] and
         artifact['native'] is False and artifact['physical_clearance']=='HOLD_NORMAL_CLEANUP_REQUIRED' and
         artifact['owner_sha256']==case['finite_roles']['image_owner']['sha256'] and
         artifact['frozen_request_sha256']==case['request']['sha256'] and
         artifact['receipt']['sha256']==case['finite_roles']['driver_receipt']['sha256'],
         'genuine exact current M14 default-link artifact authority required')
    need(root_join==artifact['current_live_postjoin'] and
         root_join['status']=='HOLD_RETAINED_BUILD_OWNERSHIP' and
         root_join['container_id']==case['target']['container_id'] and
         root_join['controller_joined_group_absent_streams_closed'] is True and
         root_join['container_retained'] is True and root_join['shared_heavy_token_retained'] is True and
         root_join['normal_cleanup_required'] is True,'actual current postjoin HOLD required')
""")
needle="old_inspect=m.parse(stable_bytes(Path(retirement['terminal_fresh_inspect']['path']),retirement['terminal_fresh_inspect']['sha256']))"
assert needle in observer;observer=observer.replace(needle,needle+"\n        need(type(old_inspect) is list and len(old_inspect)==1,'exact current single-CID inspect array');old_inspect=old_inspect[0]")
start="""        need([row['sha256'] for row in records]==[retirement['retained_ownership']['common']['sha256'],retirement['retained_ownership']['shared']['sha256']],'retained exclusion bytes differ')
        for row,role in zip(records,('common','shared')):
            need(row==retirement['retained_ownership'][role],'retained full record identity differs:'+role)"""
repl="""        request=m.parse(m.read_bounded(m.REQUEST))
        for row in records:
            m.image_record_binding(Path(row['path']),row,m.parse(m.read_bounded(Path(row['path']))),request,target,BOOT)
        need(m.parse(m.read_bounded(m.SHARED))==retirement['shared_record_from_actual_owner']['record'],'actual retained shared record content differs')"""
assert start in observer;observer=observer.replace(start,repl)
observer=observer.replace("guard_proof=selected_map[str(CAPTURE/'guard-result.json')]","guard_proof=selected_map[case['finite_roles']['guard_result']['path']]")
ast.parse(observer);(P/'observe_current_pass_image_retirement.py').write_text(observer)
# Exact archival transaction and process/mount/Docker primitives are unchanged.
def functions(text):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
oldf=functions((OLD/'cleanup_pass_image.py').read_text());newf=functions(engine)
different=[k for k in oldf if oldf[k]!=newf[k]]
assert different==['image_receipt_binding','typed_source_binding','configure'],different
write(P/'SOURCE-ALGORITHM-DELTA.json',{'scope':__doc__,'engine_functions_changed':different,'configure_delta':'Only exact current client ledger capture path and direct owner closed-proof path literals.','receipt_guard_delta':'Typed direct closed owner capture replaces unavailable historical opt-in guard schema; actual raw proofs and owner receipt equality mandatory.','archival_transaction_functions_classes_AST_identical':[k for k in oldf if oldf[k]==newf[k]],'observer_delta':'Genuine current M14 artifact/HOLD typed guard; exact inspect array decode; source-bound fresh common/shared record capture uses unchanged image_record_binding, shared content joins actual owner receipt. Cleanup/archive mechanism unchanged.','current_physical_clearance':False})
pins={p.name:ref(p) for p in P.iterdir() if p.is_file()};write(P/'SOURCE-PINS.json',pins)
print(json.dumps({'source':ref(P/'cleanup_pass_image.py'),'observer':ref(P/'observe_current_pass_image_retirement.py'),'finite_roles':len(roles),'client_count':len(clients),'algorithm_changed':different}))
