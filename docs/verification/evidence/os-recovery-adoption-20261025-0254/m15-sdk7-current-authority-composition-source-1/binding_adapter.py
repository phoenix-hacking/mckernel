"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure SOURCE27/SDK7 metadata composition. Never publishes or grants execution.
"""
import copy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from pathlib import Path
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
WINDOW_ID='new18h-20261026-bf8b8eb1832f4c94a0166f20a95642ea'
FIXED_CUTOFFS=[1793100290.0,882395.5689528405,897734.6960034363]
OLD_NONCE='8349b6a1fc6d428aa250521380cacf8d'
OLD_REQUEST_SHA='e493db82e09b412003368019bdc7f31054d79381ff0af59c916107f08903f752'
PROVIDER_SHA='89639e9d56c390968a86a95bb734128ec61bd0f6de28f7c7992cfb9e00b9ef96'
PROFILE=dict(cpus='2-5',jobs=1,memory_bytes=12*2**30,memory_swap_bytes=12*2**30,network='none',pids=512)
LABELS=('linux-ABI','libudev-ABI','selected-configure','selected-build','daemon-dynamic','daemon-imports','daemon-loader')

def need(ok,reason):
 if not ok:raise ValueError(reason)
def reference(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def bound(ref):
 need(isinstance(ref,dict) and set(ref)=={'path','bytes','sha256'},'exact-reference')
 raw=Path(ref['path']).read_bytes();need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'exact-source-or-evidence-reference');return json.loads(raw)
def validate_historical_artifact(artifact):
 need(artifact.get('decision')=='PASS_SDK_SUPPORTED_TOOLS_ARTIFACTS_ONLY' and artifact.get('contract')=='m15.bfd.supported-tools' and artifact.get('logical_commands')==21,'historical-sdk21-artifact-scope')
 need(artifact.get('implementation_ownership') is False and artifact.get('new_operation_current_physical_acceptance') is False and artifact.get('full_installation_default_native_whole_file_C_retirement_acceptance') is False,'historical-proof-cannot-grant-current-admission')
 need(isinstance(artifact.get('normal_retirement_acceptance_sha256'),str) and re.fullmatch('[0-9a-f]{64}',artifact['normal_retirement_acceptance_sha256']),'retained-sdk21-retirement-provenance')
 return True

def validate_parent(proof,aggregate_env):
 need(proof.get('window_id')==WINDOW_ID and proof.get('fixed_cutoffs')==FIXED_CUTOFFS and proof.get('deadline_utc')=='2026-10-27T11:24:50Z','same-fixed-parent-boundary')
 need(proof.get('thread_id')=='01a170fb-57c3-7ab3-862d-8005bef92a63' and proof.get('credit_run_id')=='7f4af94a83b14cc08f97401f5891d965','same-thread-credit-run')
 try:aggregate=Decimal(aggregate_env)
 except (InvalidOperation,TypeError):raise ValueError('aggregate-budget-not-decimal')
 need(isinstance(aggregate_env,str) and aggregate.is_finite() and Decimal(0)<aggregate<=Decimal('22.0439'),'current-aggregate-ceiling')
 return dict(jobs=7,aggregate_memory_GiB=aggregate_env,heavy_profile=copy.deepcopy(PROFILE))

def validate_source_relation(packet,approval,source_map):
 need(packet['profile']==PROFILE and tuple(row['label'] for row in packet['seven_commands'])==LABELS,'unchanged-seven-command-profile')
 need(approval.get('decision')=='PASS_SOURCE' and approval.get('implementation_ownership') is False and approval.get('execution_authority') is False and approval.get('SDK_execution_released') is False,'retained-source-review-scope')
 need(approval.get('request_sha256')==OLD_REQUEST_SHA,'retain-original-request-provenance')
 need(approval.get('source_sha256')==source_map.get('source_sha256') and approval.get('source_map_sha256')==packet['full11_map']['sha256'],'unchanged-full11-source-map')
 need(approval.get('provider_sha256')==packet['provider']['sha256']==PROVIDER_SHA,'unchanged-provider')
 need(approval.get('fetched_proof_sha256')==packet['fetched_source']['sha256'],'unchanged-fetched-source27')
 return True

def validate_metadata_review(review,packet,request,request_ref,adapter_refs):
 need(isinstance(request,dict) and re.fullmatch('[0-9a-f]{32}',str(request.get('nonce'))) and request['nonce']!=OLD_NONCE,'fresh-actual-request-nonce-required')
 need(request.get('request_path')==request_ref['path'] and request_ref['sha256']!=OLD_REQUEST_SHA,'new-exact-request-reference')
 need(review.get('decision')=='PASS_METADATA_SOURCE_BINDING' and review.get('reviewer') not in (None,'','/root') and review.get('implementation_ownership') is False and review.get('execution_authority') is False,'independent-metadata-relation-required')
 expected=dict(historical_source_approval=packet['source_approval'],historical_request_sha256=OLD_REQUEST_SHA,new_request=request_ref,new_nonce=request['nonce'],source_sha256=bound(packet['full11_map'])['source_sha256'],provider=packet['provider'],source27=packet['source27'],adapter_sources=adapter_refs,window_id=WINDOW_ID,fixed_cutoffs=FIXED_CUTOFFS)
 need(review.get('bindings')==expected,'exact-old-source-new-request-relation')
 return expected

def pending_composition(packet,approval,source_map,artifact,parent,parent_ref,aggregate_env):
 """Produce a concrete source-only dependency boundary, never a fake current proof."""
 validate_historical_artifact(artifact);validate_source_relation(packet,approval,source_map)
 aggregate=validate_parent(parent,aggregate_env)
 result=copy.deepcopy(packet)
 result.update(schema='mckernel.daemon7.current-authority-composition.source-only.v1',status='STATIC_SOURCE_RELATION_READY_CURRENT_TYPED_AUTHORITY_REQUIRED',source_only=True,
  window=dict(id=WINDOW_ID,start='2026-10-26T17:24:50Z',deadline='2026-10-27T11:24:50Z'),fixed_cutoffs=list(FIXED_CUTOFFS),consumed_root_window_proof=parent_ref,
  aggregate=aggregate,clock_boot_cutoff=FIXED_CUTOFFS[2],clock_monotonic_cutoff=FIXED_CUTOFFS[1],
  historical_provenance=dict(SDK21_artifact_behavior=packet['SDK21_artifact_behavior'],SDK21_normal_retirement_acceptance_sha256=artifact['normal_retirement_acceptance_sha256'],SOURCE27_source_approval=packet['source_approval'],SOURCE27_original_request_sha256=OLD_REQUEST_SHA,old_nonce=OLD_NONCE,old_aggregate_memory_GiB='22.0485'),
  current_physical=None,typed_current_authority=None,actual_admission=None,request=None,actual_nonce=None,actual_owned_capture=None,runtime_authority=None,SDK_execution_release=None,query_release=None,publication=None,source_binding_adapter=None,
  actual_dependency=dict(kind='LATEST_COMPLETED_OPERATION_TYPED_CURRENT_AUTHORITY',required=['exact latest completed serialized-operation identity','matching normal-retirement and current-physical acceptance references','existing pure typed-validator source reference and entrypoint','independent exact metadata review binding validator/proof/operation to fresh request+nonce','actual source-bound query/resources/capture/release retain their original separate gates']),
  semantic_change='Historical SDK21 retirement is retained as artifact provenance only; the latest completed operation independently supplies current admission. No old proof is relabeled.')
 # Static preparation used slightly later clock samples. Preserve it as history;
 # the earlier root boundary is the only candidate current authority.
 result['historical_static_parent_window']=result.pop('consumed_parent_window')
 result['historical_static_parent_clocks']=result.pop('consumed_parent_clocks')
 need(result['seven_commands']==packet['seven_commands'] and result['profile']==packet['profile'] and result['owner']==packet['owner'] and result['driver']==packet['driver'],'runtime-consumers-unchanged')
 return result
