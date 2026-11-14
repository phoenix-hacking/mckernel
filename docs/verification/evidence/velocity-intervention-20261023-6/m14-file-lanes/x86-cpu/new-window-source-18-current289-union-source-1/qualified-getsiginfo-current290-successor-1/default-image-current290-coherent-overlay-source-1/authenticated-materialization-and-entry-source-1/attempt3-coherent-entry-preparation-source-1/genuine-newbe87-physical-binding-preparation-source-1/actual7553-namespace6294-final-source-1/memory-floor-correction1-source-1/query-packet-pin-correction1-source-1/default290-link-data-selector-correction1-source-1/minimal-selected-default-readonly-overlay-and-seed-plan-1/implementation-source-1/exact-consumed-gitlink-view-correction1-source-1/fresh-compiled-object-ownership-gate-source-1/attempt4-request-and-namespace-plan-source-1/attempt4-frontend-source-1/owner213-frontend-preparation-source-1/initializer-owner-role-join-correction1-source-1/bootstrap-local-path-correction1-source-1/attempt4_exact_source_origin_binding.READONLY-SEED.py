"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact source-origin data joins; no owner import, live query, subprocess or mutation.
"""
from pathlib import Path
import ast,hashlib,json
DATA_BINDING = Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/CURRENT-ATTEMPT4-REQUEST-ORIGINAL69-EXACT-ORIGIN-DELTA.json')
DATA_BINDING_SHA = '628bbc38d6be3f881cca0f02468b172bf6c5bd489ec680bd2f917a468e0ab83f'

def need(value,message):
 if not value:raise RuntimeError('attempt2 binding: '+message)
def ref(path):
 path=Path(path);h=hashlib.sha256()
 with path.open('rb') as stream:
  for raw in iter(lambda:stream.read(1<<20),b''):h.update(raw)
 return dict(path=str(path),sha256=h.hexdigest(),bytes=path.stat().st_size)
def auth(row):
 need(isinstance(row,dict) and set(row)=={'path','sha256','bytes'} and ref(row['path'])==row,'exact source reference');return Path(row['path'])
def data():
 need(ref(DATA_BINDING)['sha256']==DATA_BINDING_SHA,'immutable exact source-origin data');return json.loads(DATA_BINDING.read_bytes())
def validate_source_origin(current,retention):
 b=data();expected=json.loads(auth(b['current_request']).read_bytes());origin=json.loads(auth(b['published_origin_request']).read_bytes());need(current==expected,'exact actual current4d request data')
 need(set(current)==set(origin)|{'image_receipt_candidate_sha','readonly_reuse_inputs'} and set(current)-set(origin)=={'image_receipt_candidate_sha','readonly_reuse_inputs'} and b['added_request_fields']==['image_receipt_candidate_sha','readonly_reuse_inputs'],'exact reviewed toolimage+readonlyseed keys only')
 need(current['readonly_reuse_inputs']==b['readonly_reuse_inputs']['path'],'exact readonlyseed input path');auth(b['readonly_reuse_inputs'])
 need(current['image_receipt_candidate_sha']==b['image_receipt_candidate_sha']=='942c927b1ec93cc31284ff498455909d9bb2d0fc' and current['candidate_sha']==origin['candidate_sha'],'distinct exact tool image and source candidates')
 changed=sorted(k for k in current if current[k]!=origin.get(k));need(changed==b['allowed_changed_request_fields'] and {k:current[k] for k in changed}==b['current_changed_values'],'exact reviewed role/namespace successor fields only')
 need(retention==json.loads(auth(b['source_retention']).read_bytes()) and retention['full_owner_request']==b['published_origin_request'],'genuine9793 binds original586, never relabeled4d')
 need(retention['source_manifest']==b['full_source_manifest'] and retention['source_root_identity']==current['source_identity']==current['disk_identity']==b['source_identity'],'same actual6153 source/manifest identity')
 need(retention['source_entries']==6153 and retention['source_bytes']==105804031 and retention['output_files']==46 and retention['all_reopened_content_verified'] is True,'unchanged genuine retention scope')
 actual=json.loads(auth(b['source_materialization']).read_bytes());result=json.loads(auth(b['source_copy_result']).read_bytes())
 need(actual['status']=='PASS_ONE_GRANTED_CURRENT290_SOURCE_COPY_AND_SIX_OVERLAY_READBACK_ONLY' and actual['source_identity']==current['source_identity'] and actual['source_copy_result']==b['source_copy_result'],'genuine original materialization, not a newcopy')
 need(result['source_manifest_sha256']==current['source_manifest_sha256'] and result['source_derivative_sha256']==current['source_derivative_sha256'] and result['materialization_sha256']==current['materialization_sha256'] and result['source_entries']==6153 and result['regular_files']==6104 and result['tracked_symlinks']==49 and result['copied_bytes']==105804031,'exact original copy result')
 need(current['host_owner_path']==b['host_control_owner']['path'] and current['host_owner_sha256']==b['host_control_owner']['sha256'] and current['host_owner_path']!=b['image_entry_owner']['path'],'distinct host96 and image337 roles')
 for row in [b['image_entry_owner'],b['host_control_owner'],b['full_source_manifest'],b['driver'],b['provenance']]:auth(row)
 return True

NAMESPACE_OWNER_SUCCESSION = {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1/attempt4-request-and-namespace-plan-source-1/attempt4-frontend-source-1/owner213-frontend-preparation-source-1/initializer-owner-role-join-correction1-source-1/bootstrap-local-path-correction1-source-1/EXACT-INITIALIZER15-TO-RUNTIME213-ACCEPTED-VALIDATOR-ROLE-JOIN.SOURCE-ONLY.json', 'sha256': '50efa2784b60caf3a31dcd67f39db62ad153ffc2e5fc87cfc4be10833a09d4bc', 'bytes': 13703}
ROLE_JOIN_KEYS = frozenset(['changed_constant', 'exact_whole_source_replacement', 'historical_receipt_relabel', 'host_control_owner', 'initializer_constant_value', 'initializer_owner', 'initializer_receipt', 'namespace_identities', 'namespace_reinitialization', 'new_runtime_admission_authority', 'positive_only_join', 'positive_only_stdout', 'readonly_git_allowance', 'request', 'runtime_constant_value', 'runtime_owner', 'schema', 'scope', 'validator_acceptance', 'validator_test'])

def require_initializer_runtime_owner_roles(initialized,b):
 need(b.get('initializer_owner_successor_join')==NAMESPACE_OWNER_SUCCESSION,'exact qualified namespace owner succession reference')
 joined=json.loads(auth(NAMESPACE_OWNER_SUCCESSION).read_bytes())
 need(set(joined)==ROLE_JOIN_KEYS and joined['schema']=='mckernel.current290.exact-initializer-owner15-runtime-owner213-role-join.v1','closed exact namespace owner succession record')
 need(joined['changed_constant']=='COMMON_EXCLUSION' and joined['exact_whole_source_replacement'] is True and joined['namespace_reinitialization'] is False and joined['new_runtime_admission_authority'] is False and joined['historical_receipt_relabel'] is False,'namespace succession scope')
 need(joined['initializer_receipt']==b['actual_namespace_initialization'] and initialized==json.loads(auth(joined['initializer_receipt']).read_bytes()),'original initializer receipt byte-authenticated unchanged')
 need(joined['request']==b['current_request']==initialized['request'],'exact unchanged request31 role')
 need(joined['initializer_owner']['sha256']=='15fe434d4e3ce8bea8ad280567b05ed35be4a99f590d695772d3917025ee8fe3' and joined['runtime_owner']['sha256']=='21378c973de1f12a75978e38056bb2078d933ae28e841e0c1a75e34d818e1a80','exact initializer15/runtime213 source pair')
 need(initialized['owner']==b['namespace_initializer_owner']==joined['initializer_owner'] and b['image_entry_owner']==joined['runtime_owner'],'distinct exact namespace initializer and runtime owner roles')
 need(initialized['host_control_owner']==b['host_control_owner']==joined['host_control_owner'] and initialized['identities']==b['actual_namespace_identities']==joined['namespace_identities'],'unchanged host helper and three initialized namespace IDs')
 oldraw=auth(joined['initializer_owner']).read_text();newraw=auth(joined['runtime_owner']).read_text();oldtree=ast.parse(oldraw);newtree=ast.parse(newraw)
 def common(tree):
  nodes=[n for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='COMMON_EXCLUSION']
  need(len(nodes)==1,'one exact top-level COMMON_EXCLUSION assignment');return nodes[0]
 oldnode=common(oldtree);newnode=common(newtree);request=json.loads(auth(joined['request']).read_bytes())
 need(ast.literal_eval(oldnode.value)==joined['initializer_constant_value'] and ast.literal_eval(newnode.value)==joined['runtime_constant_value']==request['common_exclusion_path'] and joined['initializer_constant_value']!=joined['runtime_constant_value'],'exact old/new COMMON namespace binding')
 expected=oldraw.replace(ast.get_source_segment(oldraw,oldnode),'COMMON_EXCLUSION = '+repr(joined['runtime_constant_value']),1)
 need(expected==newraw,'exact whole-source single COMMON assignment replacement')
 oldnode.value=newnode.value
 need(ast.dump(oldtree,include_attributes=False)==ast.dump(newtree,include_attributes=False),'whole-module AST identical except qualified COMMON constant')
 accepted=json.loads(auth(joined['validator_acceptance']).read_bytes());auth(joined['validator_test']);auth(joined['readonly_git_allowance'])
 need(accepted['decision']=='ACCEPT_THREE_REAL_OWNER_VALIDATOR_CONTROLS_ACROSS_RETAINED_RUNS' and accepted['reviewer']=='/root/f02_contract_review' and accepted['recorded_by']=='/root' and accepted['implementation_ownership'] is False and accepted['owner_sha256']==joined['runtime_owner']['sha256'] and accepted['test_sha256']==joined['validator_test']['sha256'] and accepted['original_full_suite_pass'] is False and accepted['new_heavy_admission'] is False,'genuine bounded real owner validator acceptance, no suitePASS/admission')
 need(joined['validator_test']['sha256']=='90e6d6741bb1c04a0f65b27a2bc6ba93da95c42dd71b4e1f6816921839eb5aea' and joined['readonly_git_allowance']['sha256']=='33037d9f58202271183cfd338d185c6847b17b373dbd60df45a1eb1c09df1844','exact actual validator and readonly Git allowance')
 need(joined['positive_only_join'] in accepted['evidence'] and joined['positive_only_stdout'] in accepted['evidence'],'accepted positive-only raw join/output refs')
 positive=json.loads(auth(joined['positive_only_join']).read_bytes());auth(joined['positive_only_stdout'])
 need(positive['returncode']==0 and positive['timed_out'] is False and positive['direct_child_joined'] is True and positive['group_absent'] is True and positive['closed_streams'] is True,'actual positive-only owner validator joined')
 return True

def require_new_runtime_facts(cfg):
 b=data();spec=json.loads(auth(b['physical_consumer_spec']).read_bytes())
 need(all(isinstance(spec.get(k),dict) for k in ['actual_acceptance','actual_postjoin','actual_namespace_initialization','physical_validator']) and isinstance(spec.get('namespace_identities'),list) and len(spec['namespace_identities'])==3,'genuinely new approved physical proof and namespace3 identities pending; old proofs cannot clear')
 need(cfg.get('physical')==spec['actual_acceptance'] and cfg.get('postjoin')==spec['actual_postjoin'],'exact genuinely new current physical facts')
 need(cfg.get('namespace_initialization')==spec['actual_namespace_initialization'],'exact genuinely new namespace3 receipt')
 v=spec['physical_validator'];path=auth(v)
 import types
 module=types.ModuleType('actual7553_current_proof');module.__file__=str(path);exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
 module.validate(cfg['physical'],cfg['postjoin'])
 initialized=json.loads(auth(cfg['namespace_initialization']).read_bytes())
 require_initializer_runtime_owner_roles(initialized,b)
 need(initialized['status']=='PASS_ACTUAL_ORDINARY_SOURCE_PREPARATION_NAMESPACE_INITIALIZATION_ONLY' and initialized['request']==b['current_request'] and initialized['owner']==b['namespace_initializer_owner'] and initialized['host_control_owner']==b['host_control_owner'],'genuine ordinary init exact roles')
 need(initialized['identities']==b['actual_namespace_identities']==spec['namespace_identities'] and len(initialized['identities'])==3,'exact three actual namespace identities')
 for row in initialized['identities']:need(type(row['device']) is int and row['device']>0 and type(row['inode']) is int and row['inode']>0 and row['uid']==row['gid']==1000 and row['mode']==0o700,'actual positive private namespace IDs')
 return True

