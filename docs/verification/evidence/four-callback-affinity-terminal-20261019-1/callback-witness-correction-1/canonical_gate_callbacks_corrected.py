"""Correct only the callback proof-block projection; retained original source remains pinned."""
from pathlib import Path
import hashlib,types
_LOADER={'path': '/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/callback-witness-correction-1/fixed_case_loader.py', 'sha256': '356fea4b3857eec69de71ffedc786765f00976b93e82caefc4f2abecbc19a1fd', 'bytes': 2448}
_raw=Path(_LOADER['path']).read_bytes();assert len(_raw)==_LOADER['bytes'] and hashlib.sha256(_raw).hexdigest()==_LOADER['sha256']
_module=types.ModuleType('_fixed_fresh8b_callback_loader');_module.__file__=_LOADER['path'];exec(compile(_raw,_module.__file__,'exec'),_module.__dict__)
def validate_callback_witnesses(block,required_exports):
 expected={'process_current_resource_set_bridge':8,'process_release_hash_detach_bridge':9,'process_release_sibling_detach_bridge':10,'process_release_final_cleanup_bridge':17}
 need(isinstance(block,dict) and set(required_exports)==set(expected),'exact required callback exports')
 rows=block.get('callbacks');need(isinstance(rows,list) and len(rows)==len(expected) and all(isinstance(row,dict) for row in rows),'four actual callback rows')
 symbols=[row.get('symbol') for row in rows];need(all(isinstance(symbol,str) for symbol in symbols) and len(set(symbols))==len(expected) and set(symbols)==set(expected),'unique exact actual callback exports')
 mapping=block.get('source_argument_map');need(isinstance(mapping,dict) and mapping==expected and all(type(v) is int for v in mapping.values()),'exact frozen source callback argument map')
 for row in rows:
  need(type(row.get('argument_index_from_frozen_Rust_source')) is int and row['argument_index_from_frozen_Rust_source']==expected[row['symbol']] and row.get('consumer')=='release_process' and row.get('index_convention')=='zero-based-body-result-argument','actual callback source consumer/index')
  need(row.get('machine_default_body_form')=='INLINED_PHASES_PROVEN_BY_COMPLETE_RELOCATION_PROJECTION' and row.get('machine_argument_slot_independently_decoded') is False,'actual inlined callback body and truthful machine slot')
 whole=block.get('whole_default_machine_source_association');need(isinstance(whole,dict) and whole.get('source_argument_map')==expected and whole.get('machine_argument_slot_independently_decoded') is False and whole.get('order')==['current_resource_set','hash_detach','sibling_detach','final_cleanup'],'same whole default callback phase association')
 return block
_module.apply(globals(),'canonical_gate.py')
