"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind known actual data before clock; leave Root authority/unknown receipts NULL.
"""
from pathlib import Path
import json,hashlib,re,ast,difflib
D=Path(__file__).resolve().parent;E=D.parent;T=D/'templates';F=D/'root-adopted-retirement-entry-1'
OLD=E/'m15-rust-executor-startup-native-entry-source-1/correct-rust-collector-native-entry-source-1/root40-current-binding-delta-1';S=E/'m15-rust-startup-retirement-stage-preparation-source-1/root-actual-qualified-input-plan-source-1'
NONCE='5fe0acdfcc75309f0cb40ddb1178b88b'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def js(p,x):(D/p).write_text(json.dumps(x,indent=2)+'\n')
def norm(r):return dict(path=r['path'],bytes=r.get('bytes',r.get('size')),sha256=r['sha256'])
L=ref(E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER43.json');assert L['sha256']=='41ade09947062d4f7cd4136d32d466c502e096c166519b1dba2aaa0d5a53b7f4';ledger=read(L['path']);FREE=ledger['latest_accepted_free_boundary'];assert FREE['sha256']=='221349f9f93973b57c7d6b4a69d79d9f8e6dd2dcd368d16a08fcfac88c054d0d';assert len(ledger['consumed_nonces'])==45
stage=read(S/'COLLECTOR-AND-STAGE-BINDING.json');p=read(D/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json')
for key,field in [('overlay','overlay'),('overlay_manifest','actual_receipt'),('offline_manifest','manifest')]:p[key]=norm(stage[field])
p['manifest']=dict(p['offline_manifest'],path='/home/holden/mckernel-work/scratch/m15str1-inputs/manifest.json');p['composed_case_binding']=ref(S/'COLLECTOR-AND-STAGE-BINDING.json');p['nonce']=NONCE;p['root_ledger35']=L;p['latest_serial_operation_physical_acceptance']=FREE
for flag,value in [('--manifest',p['manifest']['path']),('--manifest-sha256',p['manifest']['sha256']),('--nonce',NONCE)]:p['exact_argv'][p['exact_argv'].index(flag)+1]=value
p['status']='ACTUAL_RETIREMENT_COLLECTOR_STAGE_BOUND_ROOT_AUTHORITY_PENDING';js('STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',p)
cap=(T/'capture_fresh_startup_resource.py').read_text().replace('ROOT_FUTURE_LEDGER_NAME_REQUIRED','ROOT-CURRENT-NONCE-LEDGER43.json').replace('ROOT_FUTURE_LEDGER_SHA_REQUIRED',L['sha256']).replace('ROOT_FUTURE_LEDGER_COUNT_REQUIRED','45');(T/'capture_fresh_startup_resource.py').write_text(cap)
prep=(T/'prepare_startup_bindings.py').read_text().replace('ROOT_FUTURE_LEDGER_COUNT_REQUIRED','45').replace("adopt['artifact']","adopt['actual_artifact']").replace('reuse all16 actual startup producer controls','reuse all22 actual retirement startup producer controls');(T/'prepare_startup_bindings.py').write_text(prep)
bridge=(T/'root_once_startup_entry.py').read_text().replace("GUARD = BASE.parent.parent.parent/","GUARD = BASE.parent/").replace('ROOT_FINAL_NONCE_REQUIRED',NONCE);(T/'root_once_startup_entry.py').write_text(bridge)
c=read(D/'SOURCE-CONTEXT.json');c.update(status='ACTUAL_ROOT43_SOURCE_BOUND_KNOWN_STAGE_NO_RUNTIME_AUTHORITY',Root43=L,current_free=FREE,nonce=NONCE,Root42_historical=c['Root42'],actual_stage_binding=ref(S/'COLLECTOR-AND-STAGE-BINDING.json'),unknown_actual_only_fields=['nonce_reservation','scratch_manifest_stage','stage_map_acceptance','source_authority','case_capability','current_capture_independent_source_review'])
c['helper_sources']=[dict(name=x.name,retained=ref(OLD/'templates'/x.name),template=ref(x)) for x in sorted(T.glob('*.py'))];js('SOURCE-CONTEXT.json',c)
# Keep the existing final-fill/prepare/bridge protocol; adapt exact data/schema.
f=(OLD/'finalize_context.py').read_text().replace("F=D/'root-adopted-correct-entry-1'","F=D/'root-adopted-retirement-entry-1'")
f=re.sub(r"CONTEXT_SHA='[0-9a-f]{64}'","CONTEXT_SHA="+repr(ref(D/'SOURCE-CONTEXT.json')['sha256']),f,count=1);f=re.sub(r"STATIC_TEMPLATE_SHA='[0-9a-f]{64}'","STATIC_TEMPLATE_SHA="+repr(ref(D/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json')['sha256']),f,count=1);f=f.replace('6d2e6c210f8bf62b1a4f1abc127fb09a',NONCE)
f=f.replace("context['source_files']","context['helper_sources']").replace("context['root40_ledger']","context['Root43']").replace("context['root40_free']","context['current_free']")
f=f.replace("['compiled_collector_adoption','compiled_collector_caseprofile','compiled_collector_HOST_acceptance','compiled_collector_facts','nonce_reservation','scratch_manifest_stage','stage_map_acceptance','manifest','offline_manifest']","['compiled_collector_adoption','compiled_collector_caseprofile','compiled_collector_HOST_acceptance','compiled_collector_facts','manifest','offline_manifest']")
f=f.replace("facts['actual_test_count']==16","facts['actual_test_count']==22").replace('compiled_producer_controls_reused=16','compiled_producer_controls_reused=22').replace('new16 controls','new22 controls').replace('eb04537e8c186d413f57958451968d37ccc3519c1ac33b97fd62514ea968eb4b',p['manifest']['sha256'])
f=f.replace("['root_ledger','latest_free','source_authority','case_capability','stage_map_acceptance','current_capture_source','current_capture_independent_source_review']","['root_ledger','latest_free','source_authority','case_capability','stage_map_acceptance','nonce_reservation','scratch_manifest_stage','current_capture_source','current_capture_independent_source_review']")
oldpredicate="need(free['decision']=='PASS_CURRENT_FREE' and free['independent'] is True and free['implementation_ownership'] is False and free['current_boundary']['all_actual_client_positive_reaps'] is True and free['current_boundary']['actual_docker_clients']==30 and free['current_boundary']['all33_actor_pid_and_pgrp_absent'] is True and free['current_boundary']['lease_retained'] is False and free['current_boundary']['owner_absence_verified'] is True,'actual Root40 independent current free')"
newpredicate="need(q['root_ledger']==p['root_ledger35'] and q['latest_free']==p['latest_serial_operation_physical_acceptance'] and free['decision']=='PASS_POSITIVE_CURRENT114_FOUR_COMMAND_TERMINATION_AND_CURRENT_FREE_PERMANENT_MUTEX' and free['independent'] is True and free['implementation_ownership'] is False and free['normal_owned_retirement'] is True and free['current_free'] is True and free['holder']['pid']==1763445 and free['runner']['pid']==1763997,'actual exact Root43/latest114 free')"
assert oldpredicate in f;f=f.replace(oldpredicate,newpredicate)
f=f.replace("['source_authority','case_capability','stage_map_acceptance','current_capture_independent_source_review']","['source_authority','case_capability','stage_map_acceptance','nonce_reservation','scratch_manifest_stage','current_capture_independent_source_review']")
f=f.replace("if name=='prepare_startup_bindings.py':source=source.replace(\"['consumed_nonces'])==40\",\"['consumed_nonces'])==%d\"%len(ledger['consumed_nonces']))","if name=='prepare_startup_bindings.py':need(len(ledger['consumed_nonces'])==45,'exact Root43 literal source already filled')")
f=f.replace("('stage_map_acceptance',q['stage_map_acceptance']),","('stage_map_acceptance',q['stage_map_acceptance']),('nonce_reservation',q['nonce_reservation']),('scratch_manifest_stage',q['scratch_manifest_stage']),")
f=f.replace('PASS_CORRECT_STARTUP_ROOT40_CURRENT_BOUND_AUTHORITY_NULL','PASS_RETIREMENT_STARTUP_ROOT43_CURRENT_BOUND_AUTHORITY_NULL').replace('no stale Root40','no stale Root43')
(D/'finalize_context.py').write_text(f);ast.parse(f)
q=read(OLD/'ROOT-FINAL-FILL.TEMPLATE.NOT-AUTHORIZED.json');q.update(author=None,nonce=NONCE,root_ledger=L,latest_free=FREE,source_authority=None,case_capability=None,stage_map_acceptance=None,nonce_reservation=None,scratch_manifest_stage=None,current_capture_source=ref(T/'capture_fresh_startup_resource.py'),current_capture_independent_source_review=None,known_source_checkpoint=dict(Root43=L,latest114free=FREE,actual_stage_binding=p['composed_case_binding']),instruction='Root fills actual authority/capability/fullmapQMPstage review+scratch stage/nonce reservation/currentcapture independent review; all helpers and literalRoot43 before clocks. No capture/entry authority from this input.');js('ROOT-FINAL-FILL.TEMPLATE.NOT-AUTHORIZED.json',q)
for path in T.glob('*.py'):ast.parse(path.read_text())
# Full absolute QMP path with actual reserved nonce, before any owner/guard call.
qmp=p['attempt_parent']+'/attempt-'+NONCE+'/qmp.sock';assert len(qmp.encode())==92<108;js('QMP-ABSOLUTE-PATH-PREFLIGHT.SOURCE-ONLY.json',dict(scope=p['scope'],status='PASS_SOURCE_ACTUAL_RESERVED_NONCE_PATH_92_LT108',nonce=NONCE,absolute_socket_path=qmp,encoded_bytes=92,limit_exclusive=108,owner_source=p['owner_source'],actual_owner_API_root_receipt=None,runtime_authority=None))
for name in ['capture_fresh_startup_resource.py','prepare_startup_bindings.py','root_once_startup_entry.py']:
 before=(OLD/'templates'/name).read_text();after=(T/name).read_text();(D/(name+'.context.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='reviewedRoot40/'+name,tofile='exactRoot43/'+name)))
print('PASS exactRoot43/nonce5fe0/currentfree221/collector33c11 source data; QMP92; all runtime authority fields unfilled')
