"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact source-origin data joins; no owner import, live query, subprocess or mutation.
"""
from pathlib import Path
import ast,hashlib,json
DATA_BINDING = Path(__file__).parent / 'CURRENT-OWNER337-REQUEST4D-ORIGINAL69-ACTUAL7553-NS6294.EXACT-DATA.json'
DATA_BINDING_SHA = 'c07a38d2836d0d6e775e6409b8dd8fbb2dd47d47fcc95a2a91129154a4004cbf'

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
 need(set(current)==set(origin)|{'image_receipt_candidate_sha'} and set(current)-set(origin)=={'image_receipt_candidate_sha'},'exact reviewed added tool image candidate key only')
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
 need(initialized['status']=='PASS_ACTUAL_ORDINARY_SOURCE_PREPARATION_NAMESPACE_INITIALIZATION_ONLY' and initialized['request']==b['current_request'] and initialized['owner']==b['image_entry_owner'] and initialized['host_control_owner']==b['host_control_owner'],'genuine ordinary init exact roles')
 need(initialized['identities']==b['actual_namespace_identities']==spec['namespace_identities'] and len(initialized['identities'])==3,'exact three actual namespace identities')
 for row in initialized['identities']:need(type(row['device']) is int and row['device']>0 and type(row['inode']) is int and row['inode']>0 and row['uid']==row['gid']==1000 and row['mode']==0o700,'actual positive private namespace IDs')
 return True

