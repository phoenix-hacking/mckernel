"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One ordinary, source-only SDK7 finalization step. No live clocks or admission.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import growth_chain_validator as chain
D=Path(__file__).resolve().parent
E=D.parent
C=E/'sdk7-142g-consumer-successor-source-1'
ORIGIN=Path('/home/holden/mckernel-work/host-preparation/daemon-sdk7-new18h-source-1/CONSUMER.NEXT18H.PENDING.json')
ORIGIN_SHA='6d8ba10f30546fa9aceeca6c76da7f0c9fe050963f0e7d78dfbdc99cc6823c2d'
WINDOW=E/'m15-sdk7-current-authority-composition-source-1/WINDOW.EARLIEST-PARENT-BOUND.SOURCE-ONLY.json'
FIELDS=('growth_closure','growth_current_physical_acceptance','accepted_growth_stage','latest_operation','operation_head','live_observation','current_physical_acceptance','current_source_publication','current_source_review','actual_request')
def need(ok,why):
 if not ok:raise ValueError(why)
def render(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def dref(p,v):
 raw=render(v);return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def bound(r,document=True):
 need(isinstance(r,dict) and set(r)=={'path','bytes','sha256'},'exact-input-reference')
 raw=Path(r['path']).read_bytes();need(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],'changed-bound-input')
 return json.loads(raw) if document else raw

def prepare(out,inputs=None):
 out=Path(out).resolve();inputs={} if inputs is None else inputs
 need(set(inputs)<=set(FIELDS),'only-explicit-static-input-fields')
 inputs={key:inputs.get(key) for key in FIELDS}
 origin=bound(ref(ORIGIN));need(ref(ORIGIN)['sha256']==ORIGIN_SHA,'unchanged-SOURCE27-origin')
 original=bound(origin['request']);historical_map=bound(origin['full11_map']);mapping=bound(ref(C/'CURRENT-CONSUMER-SOURCE-MAP.NOT-REVIEWED.json'))
 owner=ref(C/'daemon_sdk_owner.142G-SOURCE-ONLY.py');adapter=ref(D/'sdk7_authority_adapter.POSTGROWTH-CHAIN.SOURCE-ONLY.py');validator=ref(D/'growth_chain_validator.py')
 need(owner['sha256']=='999713a7b4dafa034232d997872132642358aa80029244ad27e571efbf1664ee','selected-frozen-142G-owner')
 expected=dict(historical_map['source_sha256']);expected['scripts/native_running_external_modules_owner.py']=owner['sha256'];need(mapping['source_sha256']==expected,'only-current-owner-runtime-map-change')
 bindings=dict(current_growth_validator=chain.PARENT,current_owner=owner,current_source_map=ref(C/'CURRENT-CONSUMER-SOURCE-MAP.NOT-REVIEWED.json'),current_adapter=adapter,historical_owner=origin['owner'],historical_source_approval=origin['source_approval'])
 request=copy.deepcopy(original)
 for key in ('nonce','candidate_root','candidate_identity','owner_evidence_root','output_parent_identity','input_identity','basis_identity','backing_identity'):request[key]=None
 request['request_path']=str(out/'SDK7-REQUEST.TEMPLATE.NOT-RELEASED.json')
 requestref=dref(out/'SDK7-REQUEST.TEMPLATE.NOT-RELEASED.json',request)
 if inputs['actual_request'] is not None:requestref=inputs['actual_request'];request=bound(requestref)
 bundle=dict(schema='mckernel.daemon7.live-admission.v1',status='STATIC_POSTGROWTH_BINDINGS_NOT_EXECUTABLE',parent_window=ref(WINDOW),query_window=ref(WINDOW),request=requestref,current_source_map=bindings['current_source_map'],query=None,query_join=None,reservation=None,root_admission_review=None)
 for key in ('growth_closure','accepted_growth_stage','latest_operation','operation_head','live_observation','current_source_publication','current_source_review'):bundle[key]=inputs[key]
 results=dict(custody_chain='PENDING_ACTUAL_CLOSURE',parent696_and_current_head='PENDING_ACTUAL_REQUEST_HEAD_STAGE_LIVE',current_sources='PENDING_MATCHING_PUBLICATION_REVIEW')
 if inputs['growth_closure'] is not None:
  need(inputs['growth_current_physical_acceptance'] is not None,'matching-accepted-growth-physical-ref-required')
  growth=bound(inputs['growth_closure']);need(growth['fresh_physical_acceptance']==inputs['growth_current_physical_acceptance'],'same-accepted-growth-current-physical')
  chain.custody_chain(growth,bound);results['custody_chain']='PASS_RETAINED_TWO_HOP_METADATA_ONLY'
 if inputs['current_source_publication'] is not None or inputs['current_source_review'] is not None:
  need(inputs['current_source_publication'] is not None and inputs['current_source_review'] is not None,'publication-and-review-together')
  chain.current_sources(bundle,origin,historical_map,bound,adapter);results['current_sources']='PASS_BOUND_CURRENT_SOURCE_METADATA_ONLY'
 if all(inputs[key] is not None for key in ('growth_closure','accepted_growth_stage','latest_operation','operation_head','live_observation','actual_request')):
  chain.validate_growth_chain(bundle,bound(inputs['operation_head']),bound(inputs['latest_operation']),request,bound(inputs['live_observation']),bound(ref(WINDOW)),bound);results['parent696_and_current_head']='PASS_BOUND_METADATA_CONTEXT_ONLY_NO_CLOCK_READ_OR_ADMISSION'
 publication=dict(status=None,bindings=bindings,recovery_growth_validator=validator,execution_authority=False,git_remote='origin',fetched_commit=None,rows=None)
 review=dict(decision=None,implementation_ownership=False,reviewer=None,execution_authority=False,SDK_execution_released=False,source_sha256=expected,bindings=bindings,recovery_growth_validator=validator,current_source_publication=None)
 query=dict(status='STATIC_QUERY_RELATION_ONLY_NOT_RELEASED',bundle=None,adapter=adapter,current_owner=owner,current_source_map=bindings['current_source_map'],current_source_publication=inputs['current_source_publication'],current_source_review=inputs['current_source_review'],growth_closure=inputs['growth_closure'],accepted_growth_stage=inputs['accepted_growth_stage'],request=requestref,profile=origin['profile'],capture_helper=origin['capture_helper'],actual_nonce=None,aggregate_memory_GiB=None,owned_holder=None,evidence_root=None,release=None,clock=None,resources=None)
 base=['/usr/bin/python3','-B',adapter['path']]
 commands=dict(readonly_query=base+['--bundle','<ACTUAL_PREQUERY_BUNDLE.json>','--query-release-ref','<EXACT_INDEPENDENT_QUERY_RELEASE_REF.json>','--readonly-query-output','<FRESH_NONCE_ADMISSION.json>'],review_payload=base+['--bundle','<ACTUAL_COMPLETE_BUNDLE.json>','--review-payload-output','<FRESH_REVIEW_PAYLOAD.json>'],reviewed_release=base+['--bundle','<ACTUAL_COMPLETE_BUNDLE.json>','--execution-review-ref','<EXACT_EXECUTION_REVIEW_REF.json>','--reviewed-release-output','<FRESH_REVIEWED_RELEASE.json>'],ordinary_uid1000_owner=['/home/holden/anaconda3/bin/python3','-I','-B',owner['path'],'--request','<ACTUAL_NEW_REQUEST_PATH>','--request-sha256','<ACTUAL_REQUEST_SHA256>','--release','<ACTUAL_REVIEWED_RELEASE_PATH>','--release-sha256','<ACTUAL_RELEASE_SHA256>'])
 ready=dict(scope=__doc__.splitlines()[0],status='STATIC_FINALIZATION_READY_ACTUAL_CLOSURE_AND_LIVE_ADMISSION_REQUIRED',selected_owner=owner,selected_adapter=adapter,selected_chain_validator=validator,unchanged_parent696=chain.PARENT,phase_sources=chain.PHASE_SOURCES,seven_commands=origin['seven_commands'],profile=origin['profile'],provider=origin['provider'],driver=origin['driver'],historical_source27=origin['source27'],historical_sdk21=origin['SDK21_artifact_behavior'],historical_source_approval=origin['source_approval'],inputs=inputs,typed_metadata_checks=results,commands=commands,execution_authority=False,SDK_execution_released=False,live_query_calls=0,SDK_command_executions=0,live_clock=None,fresh_resources=None,new_nonce=None,resource_reservation=None,query_release=None,execution_release=None,remaining=['actual two-hop source/copy/review/pidfd-exit/real caller-tool joins/final close and matching accepted growth/current physical references','actual fetched publication and independent source review of current adapter and chain validator, preserving owner999/map957/parent696','truthful v3 current head and accepted historical growth stage; subsequent memory closure must have its own independent postjoin acceptance','fresh actual request/candidate/evidence/backing identities, new nonce and complete consumed ledger','only after static publication: actual current clocks/resources/owned query capture/reservation and exact query/execution reviews'])
 return {'SDK7-REQUEST.TEMPLATE.NOT-RELEASED.json':request,'SDK7-BUNDLE.STATIC.NOT-RELEASED.json':bundle,'CURRENT-CONSUMER-PUBLICATION.TEMPLATE.NOT-RELEASED.json':publication,'CURRENT-CONSUMER-REVIEW.TEMPLATE.NOT-RELEASED.json':review,'SDK7-QUERY.STATIC.NOT-RELEASED.json':query,'FINALIZATION-INPUTS.TEMPLATE.NOT-RELEASED.json':inputs,'READY.POSTGROWTH.STATIC-NOT-RELEASED.json':ready}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path);p.add_argument('--emit-dir',type=Path,required=True);a=p.parse_args()
 inputs=json.loads(a.inputs.read_bytes()) if a.inputs else None
 values=prepare(a.emit_dir,inputs);a.emit_dir.mkdir(mode=0o700,exist_ok=False)
 for name,value in values.items():
  with (a.emit_dir/name).open('xb') as f:f.write(render(value))
 print(json.dumps(dict(status='PASS_ORDINARY_STATIC_PREPARATION_NO_RUNTIME_OR_ADMISSION',files=len(values),directory=str(a.emit_dir))))
if __name__=='__main__':main()
