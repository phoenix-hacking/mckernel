"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root data/source final-fill only. No capture, guard, query, grant or native execution.
"""
from pathlib import Path
import argparse,ast,hashlib,json,re
D=Path(__file__).resolve().parent;T=D/'templates';F=D/'root-adopted-process235-entry-1'
NONCE='d21f4e17faf1b0b806419b1860bd0598';CASE='P-M06-01-process-exec-wait-235B'
NAMES=['capture_fresh_startup_resource.py','run_native_startup_capture.py','prepare_startup_bindings.py','bind_startup_resource.py','run_startup_resource_once.py']
def need(ok,why):
 if not ok:raise ValueError(why)
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(r):
 need(isinstance(r,dict) and ref(r['path'])==r,'genuine exact reference');return json.loads(Path(r['path']).read_bytes())
def write(p,x):
 with p.open('x') as out:json.dump(x,out,indent=2,sort_keys=True);out.write('\n')
def sources():
 ready=json.loads((D/'SOURCE-READY.json').read_bytes())
 for row in ready['source_files']:need(ref(row['path'])==row,'immutable prepared source')
 c=json.loads((D/'SOURCE-CONTEXT.json').read_bytes());p=json.loads((D/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json').read_bytes())
 for row in c['helper_sources']:need(ref(row['retained']['path'])==row['retained'] and ref(row['template']['path'])==row['template'],'retained/helper bytes')
 need(p['nonce']==NONCE and p['expected_case']==CASE and p['expected_guest_argv']==['/bin/mcexec','-t','1','0','/apps/app'],'exact original235 identity')
 for key in ['source_authority','case_capability','root_ledger35','root_runtime_grant','source_publication','runtime_authority']:need(p[key] is None,'future authority starts null')
 for key in ['compiled_collector_adoption','compiled_collector_caseprofile','compiled_collector_HOST_acceptance','compiled_collector_facts','manifest','offline_manifest','scratch_manifest_stage','composed_case_binding','executor_supplement','executor_contract']:checked(p[key])
 facts=checked(p['compiled_collector_facts']);need(facts['actual_test_count']==26 and facts['actual_collector_artifact']['sha256']==p['collector']['sha256'],'exact actual26 controls/collector')
 need(p['offline_manifest']['sha256']=='cf49bed61322fa0f1ccb6536bdd14753903c3ec3ac2b105e22ec64c809f0a86a','actual235 manifest')
 need(len(bytes.fromhex(p['expected_oracle']['stdout_hex']))==235,'original235 oracle')
 for name in NAMES+['root_once_startup_entry.py']:ast.parse((T/name).read_text())
 return p,c

def inputs(args,p,c):
 need(args.root_inputs and args.root_inputs_sha256,'Root actual final-fill input required');rr=ref(Path(args.root_inputs).resolve());need(rr['sha256']==args.root_inputs_sha256,'Root input hash');q=checked(rr)
 need(q['author']=='/root' and q['nonce']==NONCE and q['scope']==p['scope'],'Root actual original235 input')
 need(q['actual_release_ledger_is_latest'] is True and q['Root_attests_no_intervening_operation_since_boundary'] is True,'Root actual latest complete boundary')
 ledger=checked(q['root_ledger']);free=checked(q['latest_free'])
 need(q['root_ledger']['path']==c['planned_Root46_path'],'planned actual Root46 ledger')
 need(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True,'complete actual Root ledger')
 need(ledger['latest_accepted_free_boundary']==q['latest_free']==p['latest_serial_operation_physical_acceptance'],'actual unchanged latest native0ae5 boundary')
 need(free['decision']=='PASS_POSITIVE_CORRECTED_STARTUP_NATIVE_OPERATION_RETIREMENT_AND_CURRENT_FREE' and free['independent'] is True and free['implementation_ownership'] is False and free['current_free'] is True and free['normal_owned_retirement'] is True,'actual latest native retired')
 need(NONCE not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces'],'new reserved unused namespace')
 need(len(ledger['consumed_nonces'])==len(set(ledger['consumed_nonces'])),'no duplicate consumption')
 return q,rr,ledger

def main():
 a=argparse.ArgumentParser(description=__doc__);g=a.add_mutually_exclusive_group(required=True)
 for name in ['check-template','bind-current-capture','seal-source-context','bind-bridge']:g.add_argument('--'+name,action='store_true')
 a.add_argument('--root-inputs');a.add_argument('--root-inputs-sha256');args=a.parse_args();p,c=sources()
 if args.check_template:print(json.dumps(dict(status='PASS_SOURCE_TEMPLATE_ORIGINAL235_ROOT46_PENDING_AUTHORITY_NULL',runtime_authority=None)));return
 if args.bind_bridge:
  static=F/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json';b=checked(ref(static));need(b['nonce']==NONCE and b['expected_case']==CASE,'actual static235 identity')
  for row in b['capture_sources'].values():need(ref(row['path'])==row,'sealed fivehelpers')
  text=(T/'root_once_startup_entry.py').read_text();need(text.count('ROOT_FINAL_STATIC_SHA256')==1,'single static slot');text=text.replace('ROOT_FINAL_STATIC_SHA256',ref(static)['sha256']);text=re.sub(r"HELPER_SHA = '[0-9a-f]{64}'",'HELPER_SHA = '+repr(ref(F/'run_native_startup_capture.py')['sha256']),text,count=1);ast.parse(text)
  with (F/'root_once_startup_entry.py').open('x') as out:out.write(text)
  print(json.dumps(dict(status='ONCE_BRIDGE_SOURCE_BOUND_NOT_AUTHORIZATION',bridge=ref(F/'root_once_startup_entry.py'))));return
 q,rr,ledger=inputs(args,p,c);count=len(ledger['consumed_nonces'])
 if args.bind_current_capture:
  s=(T/'capture_fresh_startup_resource.py').read_text();need(s.count('ROOT_CURRENT_LEDGER_SHA256')==1 and s.count("'ROOT_CURRENT_CONSUMED_COUNT'")==1,'finite current slots')
  s=s.replace('ROOT_CURRENT_LEDGER_SHA256',q['root_ledger']['sha256']).replace("'ROOT_CURRENT_CONSUMED_COUNT'",str(count));ast.parse(s)
  with (D/'CURRENT-BOUND-CAPTURE.SOURCE-ONLY.py').open('x') as out:out.write(s)
  print(json.dumps(dict(status='CURRENT_CAPTURE_SOURCE_BOUND_FOR_INDEPENDENT_REVIEW_NOT_EXECUTED',capture=ref(D/'CURRENT-BOUND-CAPTURE.SOURCE-ONLY.py'),root_ledger=q['root_ledger'],latest_free=q['latest_free'],consumed_count=count)));return
 for key in ['source_authority','case_capability','stage_map_acceptance','nonce_reservation','scratch_manifest_stage','current_capture_independent_source_review']:checked(q[key])
 need(q['scratch_manifest_stage']==p['scratch_manifest_stage'],'actual235 typed scratchstage')
 capture=Path(q['current_capture_source']['path']);need(ref(capture)==q['current_capture_source'],'bound capture exactbytes');s=capture.read_text();ast.parse(s)
 expected=(T/'capture_fresh_startup_resource.py').read_text().replace('ROOT_CURRENT_LEDGER_SHA256',q['root_ledger']['sha256']).replace("'ROOT_CURRENT_CONSUMED_COUNT'",str(count));need(s==expected,'only exact currentledger literal fills')
 review=checked(q['current_capture_independent_source_review']);need(review.get('implementation_ownership') is False and review.get('reviewer') not in (None,'/root') and str(review.get('decision','')).startswith('PASS') and q['current_capture_source']['sha256'] in json.dumps(review),'independent actual current capture source PASS')
 need(not F.exists(),'fresh235 sealed context only');F.mkdir(mode=0o700)
 for name in NAMES:
  text=s if name=='capture_fresh_startup_resource.py' else (T/name).read_text()
  if name=='prepare_startup_bindings.py':need(text.count("'ROOT_CURRENT_CONSUMED_COUNT'")==1,'single prepare count slot');text=text.replace("'ROOT_CURRENT_CONSUMED_COUNT'",str(count))
  ast.parse(text)
  with (F/name).open('x') as out:out.write(text)
 for key in ['source_authority','case_capability','stage_map_acceptance','nonce_reservation','scratch_manifest_stage']:p[key]=q[key]
 p['root_ledger35']=q['root_ledger'];p['capture_helper']=ref(F/'run_native_startup_capture.py');p['capture_sources']={n:ref(F/n) for n in NAMES};p['source_only_QMPproof']=q['stage_map_acceptance'];p['root_final_fill_source_input']=rr;p['current_capture_independent_source_review']=q['current_capture_independent_source_review'];p['status']='ROOT_FINAL_FILLED_ORIGINAL235_STATIC_NOT_RUNTIME_RELEASE'
 write(F/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',p);write(F/'ACTUAL-SCRATCH-MANIFEST-STAGE.json',checked(p['scratch_manifest_stage']))
 print(json.dumps(dict(status='ROOT_ORIGINAL235_SOURCE_CONTEXT_SEALED_NOT_RUNTIME_RELEASE',output=str(F),next_exact_argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(F/'prepare_startup_bindings.py'),'--check-static'])) )
if __name__=='__main__':main()
