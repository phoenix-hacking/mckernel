"""Functional OS only; no security testing. Root data/source final-fill, never capture.
All release/current fields start null. No sourceauthority, grant, observation or runtime generated.
"""
import argparse,ast,copy,hashlib,json,os,re
from pathlib import Path
D=Path(__file__).resolve().parent;T=D/'templates';F=D/'root-adopted-correct-entry-1'
CONTEXT_SHA='d2c1dd2cca403d8f9a9725fdc658f405a0dac6ed6577d5e2c27d924d94ecf3e5'
STATIC_TEMPLATE_SHA='db1dd165e4c5a1df88ed0f8152817ade4a5978b3ff2a7d862ef1e07baffffe5e'
NONCE='6d2e6c210f8bf62b1a4f1abc127fb09a'
CAPTURE_NAMES=['capture_fresh_startup_resource.py','run_native_startup_capture.py','prepare_startup_bindings.py','bind_startup_resource.py','run_startup_resource_once.py']
def need(ok,message):
 if not ok:raise ValueError(message)
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(r):
 need(ref(r['path'])==r,'exact Root reference');return json.loads(Path(r['path']).read_bytes())
def write(path,x):
 with path.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def template_check():
 need(ref(D/'SOURCE-CONTEXT.json')['sha256']==CONTEXT_SHA and ref(D/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json')['sha256']==STATIC_TEMPLATE_SHA,'exact finite context/template preimages')
 p=json.loads((D/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json').read_bytes());context=json.loads((D/'SOURCE-CONTEXT.json').read_bytes())
 for row in context['source_files']:
  need(ref(row['retained']['path'])==row['retained'],'retained source preimage');need(ref(row['template']['path'])==row['template'],'exact proposed helper postimage')
 for name in CAPTURE_NAMES+['root_once_startup_entry.py']:ast.parse((T/name).read_bytes())
 for key in ['source_authority','case_capability','root_ledger35','latest_serial_operation_physical_acceptance','root_runtime_grant','source_publication','runtime_authority']:need(p[key] is None,'future field not null '+key)
 need(p['nonce']==NONCE and p['expected_guest_argv']==['/bin/mcexec','-t','1','0','app','A','','B'],'reserved corrected case identity')
 for key in ['compiled_collector_adoption','compiled_collector_caseprofile','compiled_collector_HOST_acceptance','compiled_collector_facts','nonce_reservation','scratch_manifest_stage','stage_map_acceptance','manifest','offline_manifest']:read(p[key])
 facts=read(p['compiled_collector_facts']);need(facts['actual_test_count']==16 and facts['actual_collector_artifact']['sha256']==p['collector']['sha256'],'new16 controls and exact producer')
 need(p['manifest']['sha256']=='eb04537e8c186d413f57958451968d37ccc3519c1ac33b97fd62514ea968eb4b','actual corrected scratch manifest')
 return p,context

def main():
 a=argparse.ArgumentParser(description=__doc__);g=a.add_mutually_exclusive_group(required=True);g.add_argument('--check-template',action='store_true');g.add_argument('--seal-source-context',action='store_true');g.add_argument('--bind-bridge',action='store_true');a.add_argument('--root-inputs');a.add_argument('--root-inputs-sha256');args=a.parse_args();p,c=template_check()
 if args.check_template:print(json.dumps(dict(status='PASS_CORRECT_STARTUP_ENTRY_SOURCE_TEMPLATE_CURRENT_AND_RELEASE_NULL',nonce=NONCE,normal_helper_algorithm_unchanged=True,compiled_producer_controls_reused=16,runtime_authority=None)));return
 if args.bind_bridge:
  static=F/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json';x=json.loads(static.read_bytes());need(x['nonce']==NONCE,'actual new static identity')
  for r in x['capture_sources'].values():need(ref(r['path'])==r,'sealed capture source')
  source=(T/'root_once_startup_entry.py').read_text();need(source.count('ROOT_FINAL_STATIC_SHA256')==1,'single static placeholder');source=source.replace('ROOT_FINAL_STATIC_SHA256',ref(static)['sha256'])
  helper=ref(F/'run_native_startup_capture.py');source=re.sub(r"HELPER_SHA = '[0-9a-f]{64}'","HELPER_SHA = %r"%helper['sha256'],source,count=1);ast.parse(source)
  with (F/'root_once_startup_entry.py').open('x') as out:out.write(source)
  print(json.dumps(dict(status='NORMAL_ONCE_BRIDGE_SOURCE_BOUND_NOT_AUTHORIZATION',bridge=ref(F/'root_once_startup_entry.py'),static=ref(static),runtime_authority=None)));return
 need(args.root_inputs and args.root_inputs_sha256,'Root exact final-fill input required');rootref=dict(path=str(Path(args.root_inputs).resolve()),bytes=Path(args.root_inputs).stat().st_size,sha256=args.root_inputs_sha256);q=read(rootref)
 need(q['author']=='/root' and q['nonce']==NONCE and q['scope']==p['scope'],'actual Root final-fill source facts')
 need(q['actual_release_ledger_is_latest'] is True and q['Root_attests_no_intervening_operation_since_boundary'] is True,'no stale Root39 source authority after another operation')
 for key in ['root_ledger','latest_free','source_authority','case_capability','stage_map_acceptance','current_capture_source','current_capture_independent_source_review']:need(isinstance(q[key],dict),'genuine Root reference required '+key)
 ledger=read(q['root_ledger']);free=read(q['latest_free']);need(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True,'complete actual Root ledger')
 need(ledger['latest_accepted_free_boundary']==q['latest_free'] and NONCE not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces'],'actual latest free/new nonce')
 need(free['independent'] is True and free['implementation_ownership'] is False and free['normal_owned_retirement'] is True and free['current_free'] is True,'actual independent current free')
 for key in ['source_authority','case_capability','stage_map_acceptance','current_capture_independent_source_review']:read(q[key])
 # Current source must itself name exact new boundary. Root39 candidate is merely
 # a known source checkpoint, unusable after F05 or another operation intervenes.
 capture=Path(q['current_capture_source']['path']);need(ref(capture)==q['current_capture_source'],'independently reviewed actual current capture source');cs=capture.read_text();ast.parse(cs)
 capture_review=read(q['current_capture_independent_source_review']);need(capture_review.get('implementation_ownership') is False and capture_review.get('reviewer') not in (None,'/root') and str(capture_review.get('decision','')).startswith('PASS') and q['current_capture_source']['sha256'] in json.dumps(capture_review),'independent current capture source decision/bytes')
 need(q['root_ledger']['sha256'] in cs and q['latest_free']['sha256'] in cs,'capture pins actual latest ledger/free bytes')
 need('1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0' in cs and '2b7362126fbe70475a208e40df9eb56fa12df0993d83d0aa9b9a22a36638481c' in cs,'retained guard/baseline physical observer')
 need(not F.exists(),'fresh sealed source context only');F.mkdir(mode=0o700)
 for name in CAPTURE_NAMES:
  source=cs if name=='capture_fresh_startup_resource.py' else (T/name).read_text()
  if name=='prepare_startup_bindings.py':source=source.replace("['consumed_nonces'])==39","['consumed_nonces'])==%d"%len(ledger['consumed_nonces']))
  with (F/name).open('x') as out:out.write(source)
 for key,value in [('source_authority',q['source_authority']),('case_capability',q['case_capability']),('stage_map_acceptance',q['stage_map_acceptance']),('root_ledger35',q['root_ledger']),('latest_serial_operation_physical_acceptance',q['latest_free'])]:p[key]=value
 p['capture_helper']=ref(F/'run_native_startup_capture.py');p['capture_sources']={name:ref(F/name) for name in CAPTURE_NAMES};p['source_only_QMPproof']=q['stage_map_acceptance']
 p['root_final_fill_source_input']=rootref;p['current_capture_independent_source_review']=q['current_capture_independent_source_review'];p['status']='ROOT_FINAL_FILLED_CORRECT_STARTUP_STATIC_TEMPLATE_NOT_RUNTIME_RELEASE'
 write(F/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',p)
 stage=read(p['scratch_manifest_stage']);write(F/'ACTUAL-SCRATCH-MANIFEST-STAGE.json',stage)
 print(json.dumps(dict(status='ROOT_CURRENT_SOURCE_CONTEXT_SEALED_NOT_RUNTIME_RELEASE',output=str(F),source_files=p['capture_sources'],next_exact_argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(F/'prepare_startup_bindings.py'),'--check-static'],runtime_authority=None)))
if __name__=='__main__':main()
