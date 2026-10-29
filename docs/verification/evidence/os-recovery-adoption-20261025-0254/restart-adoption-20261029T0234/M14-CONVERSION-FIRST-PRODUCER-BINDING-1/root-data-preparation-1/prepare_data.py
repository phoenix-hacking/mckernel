#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare non-authority Root templates from existing retained build and snapshot data.
"""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;A=P.parent
SNAP=A/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1'
CF=A/'M14-CONVERSION-FIRST-COMPOSITION-1'
PROFILE=A/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/LIVE-REVALIDATION-CAP-CORRECTION-1/current119/PROFILE.SOURCE-ONLY.json'
OLD_EXPORT=A/'ROOT-CURRENT119-BUILD-ADMISSION-1/ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'
ORIGIN=A/'ROOT65-CURRENT119-ADOPTION-1/ORIGIN119-PRODUCER.ACTUAL.json'
SOURCE=P/'current-frontier-successor-1/SOURCE-READY.json'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p):return json.loads(Path(p).read_text())
def verify(r):assert ref(r['path'])==r;return r
manifest=SNAP/'EXACT-RUST-SNAPSHOT-MANIFEST.ACTUAL.json';export=SNAP/'SOURCE-EXPORT.ACTUAL.json'
assert ref(manifest)['sha256']=='18ac3dc3b6a79e49817adda73983f7340bf5a201fd2fd914ab43ed33c01d8f57' and ref(export)['sha256']=='08b1cacd2b222978e4a29b3445e63771220f05f441ca78fa3f2c25f408c3d0b7'
assert ref(P/'THREE-COMMANDS.SOURCE-ONLY.json')['sha256']=='79a0054d5771b4bdb1bade8156c77533a31d5d68b17a5c41daa31cc36947159b'
assert ref(CF/'SOURCE-READY.json')['sha256']=='caef14198a096315e21380de49982772d8070a6489ec91d4d2f0c4d2dde3473e'
assert ref(SOURCE)['sha256']=='0309142978b60a38bf8ec2fdbb897cacb66810059b79d0b870e1ee8d8f55f6c3'
profile=load(PROFILE);recipe=load(P/'THREE-COMMANDS.SOURCE-ONLY.json');sm=load(manifest);ex=load(export);oe=load(OLD_EXPORT);origin=load(ORIGIN)
assert ex['author']=='/root' and ex['compiler_calls']==0 and ex['native_calls']==0 and ex['source_files']==149 and ex['rust_files']==138
assert len(sm['files'])==149 and sum(r['relative'].endswith('.rs') for r in sm['files'])==138
assert ex['snapshot_map']==ref(P/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json')
assert sm['export_root']==str(SNAP/'rust-subtree') and sm['external_inputs']==profile['inputs']['external_relative_modules']
expected={r['relative']:r['source'] for r in load(P/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json')['entries']}
observed={r['relative']:r for r in ex['files']};assert len(expected)==len(observed)==149
assert {r['relative'] for r in sm['files']}==set(expected)==set(observed)
for row in sm['files']:
 name=row['relative'];assert row['snapshot']==observed[name]['snapshot'] and observed[name]['source']==expected[name]
 assert row['snapshot']['sha256']==expected[name]['sha256'] and row['snapshot']['bytes']==expected[name]['bytes']
assert origin['author']=='/root' and origin['returncode']==0 and origin['child_positive_join'] is True and origin['compiler'] is False and origin['runtime_authority'] is None
for v in origin['outputs']:verify(v)
assert profile['origin_source_materialization']['actual_origin_producer']==ref(ORIGIN)
assert oe['author']=='/root' and oe['SDK21_recompiled'] is False and oe['source6153_entries']==6153 and len(oe['additional_readonly_exports'])==20
retained=recipe['retained_inputs'];assert len(retained)==9
for row in retained:verify(row['source'])
assert [r for r in retained if r['link_token'].endswith('/arch/x86_64/kernel/syscall.c.o')][0]['source']['sha256']=='30bddb4cf0e8083fcce83fe691410b6d4a0e8eabec3cb6ce3b6ab190be8ab3da'
config=profile['inputs']['configuration']
for row in config:verify(row['source'])
inputs=load(CF/'AFFECTED-UNIT-CANDIDATE-INPUTS.json')
assert [r['link_token'] for r in inputs['original_link_order'] if 'source' in r]==[r['link_token'] for r in retained]
request={'scope':SCOPE,'schema':'mckernel.conversion-first-request-template.v1','author':None,'status':'TEMPLATE_ONLY_NOT_ROOT_AUTHORED','candidate':ref(CF/'SOURCE-READY.json'),'recipe':ref(P/'THREE-COMMANDS.SOURCE-ONLY.json'),'snapshot_map':ref(P/'SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json'),'actual_snapshot_manifest':ref(manifest),'actual_snapshot_export':ref(export),'predecessor_profile':ref(PROFILE),'original_origin_receipt':ref(ORIGIN),'runtime_authority':None}
reuse={'scope':SCOPE,'schema':'mckernel.conversion-first-reuse-descriptor-template.v1','author':None,'status':'TEMPLATE_ONLY_NOT_ROOT_AUTHORED','candidate':request['candidate'],'recipe':request['recipe'],'historical_eight_object_descriptor':ref(profile['reuse_descriptor']),'actual_current119_export_authority_historical_only':ref(OLD_EXPORT),'configuration':config,'retained_objects':retained,'new_object_tokens':['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o'],'original_link_order':inputs['original_link_order'],'retained_sdk21':'EXACT_CURRENT119_PROFILE_AND_HISTORICAL_EXPORT_NO_RECOMPILE','source6153':profile['inputs']['source6153'],'retained_seed':profile['inputs']['retained_seed'],'toolchain_mounts':profile['inputs']['toolchain_mounts'],'toolchain_manifest':profile['inputs']['toolchain_manifest'],'original_origin':profile['origin_source_materialization'],'runtime_authority':None}
root=load(P/'current-frontier-successor-1/ROOT-INPUT.TEMPLATE.NOT-AUTHORITY.json');root['candidate_snapshot_manifest']=ref(manifest);root['origin_receipt']=ref(ORIGIN);root['origin_directory']=str(Path(origin['outputs'][0]['path']).parent)
assert root['author'] is None and all(root[k] is None for k in ['request','reuse_descriptor','nonce','current_free','current_ledger','current_bindings','runtime_guard','runtime_guard_source_review','armed_controls','control_bundle','cutoffs'])
refs={'scope':SCOPE,'status':'EXACT_RETAINED_REFS_SOURCE_ONLY_NO_CURRENT_AUTHORITY','snapshot_manifest':ref(manifest),'snapshot_export':ref(export),'predecessor_profile':ref(PROFILE),'original_origin_receipt':ref(ORIGIN),'original_origin_outputs':origin['outputs'],'actual119_input_export_historical_only':ref(OLD_EXPORT),'producer_successor_source':ref(SOURCE),'review_state':'Actual current custody/nonce/weekly/resource inputs intentionally unbound','runtime_authority':None}
for name,data in [('ROOT-REQUEST.TEMPLATE.NOT-AUTHORITY.json',request),('REUSE-DESCRIPTOR.TEMPLATE.NOT-AUTHORITY.json',reuse),('ROOT-INPUT.PARTIAL.TEMPLATE.NOT-AUTHORITY.json',root),('EXACT-RETAINED-REFS.json',refs)]:
 (D/name).write_text(json.dumps(data,indent=2)+'\n')
print('PASS_EXACT_RETAINED_ROOT_DATA_TEMPLATES')
