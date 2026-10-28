"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root data filler. Static mode has no effects; --held uses reviewed BFD guard clock only. No source export, holder or workload.
"""
from pathlib import Path
import argparse,hashlib,json,importlib.util
D=Path(__file__).resolve().parent

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def checked(r):
 assert ref(r['path'])==r,'exact actual Root reference';return read(r['path'])
def write(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def fill(q):
 assert q['author']=='/root' and q['Root_attests_latest_Root61_no_intervening_operation'] is True
 pins=read(D/'FROZEN-COHORT-PINS.json');A=Path(pins['admission']);contract=checked(pins['contract']);ledger=checked(contract['Root61_observer_fragment']['current_ledger'])
 assert len(q['nonce'])==32 and all(c in '0123456789abcdef' for c in q['nonce']) and q['nonce'] not in ledger['consumed_nonces']
 assert q['other_reserved_memory_bytes']==2<<30 and q['other_reserved_pids']==64 and q['aggregate_pid_budget']==576
 # These independent source/config reviews are actual Root supplied references.
 for key in ['facade_configuration','common_dependency_review','physical_configuration_review','physical_configuration','top_dependency_review','observer_schema_review']:checked(q[key])
 static={k:pins[k] for k in ['profile','runner','worker','holder_source','input_export','request_payload']}
 helpers=['finite_review.py','capture_resources.py','handoff_common.py','root_capture_once.py','publish_approved_ready.py','publish_after_independent_pass_once.py','prepare_entry_inputs.py','bfd_guard_facade.py','observe_bfd_current61.py','observe_bfd_current60_history.py','observe_bfd_root59_history.py']
 static.update({name:ref(D/name) for name in helpers})
 b=dict(scope=contract['scope'],admission=str(A),nonce=q['nonce'],reviewer='/root/observerreview',Root_must_not_execute_approver=True,Root_capture_owner='/root',static_refs=static,contract=pins['contract'],source_publication=q['source_publication'],guard_facade=ref(D/'bfd_guard_facade.py'),guard_configuration=q['facade_configuration'],observer_source=ref(D/'observe_bfd_current61.py'),observer_schema=ref(D/'OBSERVER-SCHEMA.BFD.SOURCE-ONLY.json'),observer_schema_review=q['observer_schema_review'],finite_verifier=ref(D/'finite_review.py'),capture_source=ref(D/'capture_resources.py'),publisher_source=ref(D/'publish_approved_ready.py'),authorized_cutoffs=pins['clamps'],Root_data=q)
 physical=checked(q['physical_configuration'])
 assert physical['guard_adapter']==b['guard_facade'] and physical['guard_config']==b['guard_configuration'] and physical['independent_review']==q['physical_configuration_review']
 common=dict(schema='mckernel.configured-root59-observer-dependencies.v1',author='/root',observer=ref(D/'observe_bfd_root59_history.py'),nonce_ledger=read(D/'ACTUAL-PINS.json')['ledger59'],account_window_guard=b['guard_facade'],account_window_guard_configuration=b['guard_configuration'],physical_history_observer=physical['successor_source'],physical_history_configuration=q['physical_configuration'],independent_dependency_review=q['common_dependency_review'],runtime_authority=None)
 # Root59 is retained history inside the Root61 extension, never mislabeled61.
 write(D/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json',common)
 write(D/'ROOT61-RUNTIME-DEPENDENCIES.json',dict(author='/root',observer=b['observer_source'],ledger=contract['Root61_observer_fragment']['current_ledger'],guard_adapter=b['guard_facade'],guard_configuration=b['guard_configuration'],independent_review=q['top_dependency_review'],runtime_authority=None))
 if q['Root_authorizes_one_holder_only_bootstrap'] is True:
  bootstrap=dict(author='/root',decision='GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER',maximum_invocations=1,nonce=q['nonce'],permanent_mutex_path=q['permanent_mutex_path'],fresh_handshake_root=str(A/'HOLDER'),native_custody_clearance=contract['Root61_observer_fragment']['latest_free'],source=pins['holder_source'],runner=pins['runner'],worker=pins['worker'],profile=pins['profile'],scope=contract['scope'],runtime_authority=None)
  write(A/'ROOT-HOLDER-BOOTSTRAP-GRANT.json',bootstrap)
 for name in ['ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json','ROOT61-RUNTIME-DEPENDENCIES.json','ACTUAL-PINS.json','FROZEN-COHORT-PINS.json','OBSERVER-SCHEMA.BFD.SOURCE-ONLY.json']:static[name]=ref(D/name)
 for key in ['facade_configuration','common_dependency_review','physical_configuration','physical_configuration_review','top_dependency_review','observer_schema_review']:static[key]=q[key]
 write(D/'ENTRY-BINDINGS.json',b)
 return b

def fill_held(b,physical_ref,at_epoch):
 # Timestamp supplied by Root via the reviewed filler, after actual physical.
 q=b['Root_data'];A=Path(b['admission']);pins=checked(b['contract'])['Root61_observer_fragment'];physical=checked(physical_ref)
 assert physical['current_boundary']==pins['current_ledger'] and physical['observed_clocks'][0]<=at_epoch
 ready=ref(A/'HOLDER/HOLDER.READY.json');bootstrap=ref(A/'ROOT-HOLDER-BOOTSTRAP-GRANT.json')
 return dict(author='/root',decision='BIND_BFD_ACTUAL_HELD_BUILD_RESOURCES',maximum_invocations=1,nonce=b['nonce'],root_attests_only_intervening_holder_preparation=q['root_attests_only_intervening_holder_preparation'],actual_reservations_attested=q['actual_reservations_attested'],profile=b['static_refs']['profile'],nonce_ledger=pins['current_ledger'],native_custody_clearance=pins['latest_free'],physical_observation=physical_ref,holder_ready=ready,holder_bootstrap=bootstrap,at_epoch=at_epoch,other_reserved_memory_bytes=q['other_reserved_memory_bytes'],other_reserved_pids=q['other_reserved_pids'],aggregate_pid_budget=q['aggregate_pid_budget'],fresh_output_root=checked(b['static_refs']['profile'])['actual_output_root'])

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root-input',type=Path);p.add_argument('--root-input-sha256');p.add_argument('--held',action='store_true');a=p.parse_args()
 if a.held:
  b=read(D/'SEALED-ENTRY-BINDINGS.json');A=Path(b['admission']);r=b['guard_facade'];assert ref(r['path'])==r
  s=importlib.util.spec_from_file_location('Root_prebound_BFD_guard_clock',r['path']);g=importlib.util.module_from_spec(s);s.loader.exec_module(g);g.configure(b['guard_configuration']);now=g.guard()
  write(A/'ROOT-ACTUAL-RESOURCE-INPUT-1.json',fill_held(b,ref(A/'ROOT-PREHOLDER-PHYSICAL-1.json'),now[0]))
 else:
  assert ref(a.root_input)['sha256']==a.root_input_sha256;print(json.dumps(fill(read(a.root_input))))
