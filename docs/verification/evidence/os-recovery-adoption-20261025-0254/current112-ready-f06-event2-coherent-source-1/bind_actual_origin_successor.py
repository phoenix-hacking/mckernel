"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind existing genuine Root source/producer evidence; no execution/materialization.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
D=Path(__file__).resolve().parent
O=D/'oci-origin-bind-correction-source-1'
S=D/'actual-origin-bound-source-1'
S.mkdir(exist_ok=True)

def read(p):return json.loads(p.read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def write(name,b):
 p=S/name;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b and not p.is_symlink(),name
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(name,x):return write(name,json.dumps(x,indent=2)+'\n')
receipt_path=O/'ROOT-ACTUAL-ORIGIN-PRODUCER-RESULT.json';receipt=read(receipt_path)
adoption_path=D/'root-source-adoption-1/ROOT-SOURCE-ADOPTION.json';adoption=read(adoption_path)
assert receipt['author']=='/root' and receipt['returncode']==0 and receipt['direct_child_joined'] is True and receipt['streams_closed'] is True
assert ref(receipt_path)==adoption['actual_origin_producer']
header=receipt['actual_header'];auth(header)
assert header['bytes']==268 and header['sha256']=='aeece54c3b6f01c326fff3eb925b89b88acd3b198b0047393c8c9c0d78f74ded'
assert adoption['author']=='/root' and adoption['status']=='ROOT_SOURCE_ADOPTED_QUALIFIED_F03_EVENT2_AND_F06_ALLOC_FREE_ORIGIN_NOT_BUILT'
for row in adoption['files']:
 auth(row['canonical']);auth(row['private_source']);assert row['canonical']['sha256']==row['private_source']['sha256']
assert len(adoption['files'])==7
output=Path(header['path']).parent
origin_binding=read(output/'ORIGIN-BINDING.json');env=read(output/'rust-environment.json')
p=read(O/'PROFILE.SOURCE-ONLY.json');old=copy.deepcopy(p)
assert origin_binding['command']==p['exact_commands'][2]
assert origin_binding['profile_sha256']==ref(D/'candidate/scripts/f06_origin_command_profile.json')['sha256']
assert origin_binding['source_sha256']==ref(D/'candidate/arch/x86_64/kernel/syscall.c')['sha256']
assert origin_binding['source_path']==str(D/'candidate/arch/x86_64/kernel/syscall.c')
origin=origin_binding['origin_utf8'];assert origin=='/src/arch/x86_64/kernel/syscall.c'
assert origin_binding['origin_bytes_with_nul']==list(origin.encode()+b'\0')
assert env=={'MCKERNEL_F06_RT_SIGRETURN_ORIGIN':origin}
assert p['exact_commands'][0]['argv'].count('MCKERNEL_F06_RT_SIGRETURN_ORIGIN='+origin)==1
assert '#define MCKERNEL_F06_RT_SIGRETURN_ORIGIN '+json.dumps(origin) in Path(header['path']).read_text()
relative='kernel/rust/f06-origin/f06_rt_sigreturn_origin.h'
row=next(r for r in p['inputs']['postimages'] if r['relative']==relative)
preview=row['postimage'];assert preview['sha256']==header['sha256'] and preview['bytes']==header['bytes']
row['postimage']=header
assert row.pop('source_preview_not_runtime_producer') is True
row['actual_origin_producer_receipt']=ref(receipt_path)
for r in p['cohort_source_bindings']:
 if r['relative']==relative:assert r['postimage']==preview;r['postimage']=header
p['status']='CURRENT112_ROOT_SOURCE_ADOPTED_ACTUAL_ORIGIN_BOUND_BUILD_NOT_RELEASED'
p['actual_root_adoption']=ref(adoption_path)
materialization=p['origin_source_materialization']
materialization.update(status='ACTUAL_ROOT_SOURCE_PRODUCER_COMPLETE_NOT_BUILD_OR_NATIVE_ACCEPTANCE',source_only=True,actual_producer_receipt=ref(receipt_path),actual_generated_header=header,actual_origin_binding=ref(output/'ORIGIN-BINDING.json'),actual_Rust_environment=ref(output/'rust-environment.json'),actual_CMake_origin=ref(output/'f06_rt_sigreturn_origin.cmake'),producer_elapsed_seconds=receipt['finished_at']-receipt['started_at'])
assert p['exact_commands']==old['exact_commands']
assert p['inputs']['objects']==old['inputs']['objects']
assert p['inputs']['source_directory_exports']==old['inputs']['source_directory_exports']
assert sum(not r['replace'] for r in p['inputs']['objects'])==8
assert all(p[k] is None for k in ['runtime_authority','request_sha256','native_custody_clearance','actual_nonce','actual_execution_review','actual_resource_authority','actual_output_root','actual_holder'])
save('PROFILE.SOURCE-ONLY.json',p)
export=read(O/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json')
assert sum(r==preview for r in export['qualified_readonly_files'])==1
export['qualified_readonly_files']=[header if r==preview else r for r in export['qualified_readonly_files']]
export['status']='CURRENT112_ACTUAL_ORIGIN_BOUND_EXPORT_TEMPLATE_NOT_AUTHORITY'
export['actual_origin_producer_receipt']=ref(receipt_path)
export['actual_origin_context']=[ref(output/n) for n in ['ORIGIN-BINDING.json','rust-environment.json','f06_rt_sigreturn_origin.cmake']]
save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
plan=read(O/'EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json');plan['source_profile']=ref(S/'PROFILE.SOURCE-ONLY.json')
save('EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json',plan)
tools=[]
for name in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 text=(O/name).read_text();ast.parse(text,filename=name);target=write(name,text)
 tools.append(dict(name=name,predecessor=ref(O/name),successor=ref(target),byte_identical=True))
# Reuse the retained profile/source invariants, without invoking any guard/runner/producer.
source_map_path=Path(p['inputs']['source_directory_exports'][0]['manifest']['path'])
assert ref(source_map_path)==p['inputs']['source_directory_exports'][0]['manifest']
source_map=read(source_map_path);assert len(source_map['files'])==113
for r in source_map['files']:auth(r['snapshot'])
for r in p['inputs']['configuration']:auth(r['source'])
for r in p['inputs']['objects']:auth(r['source'])
for r in p['inputs']['postimages']:auth(r['postimage'])
assert p['cohort_source_bindings']==[dict(relative=r['relative'],postimage=r['postimage']) for r in p['inputs']['postimages']]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in source_map['files']]
assert export['qualified_readonly_files']==[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in p['inputs']['postimages']]+[r['snapshot'] for r in source_map['files']]
assert not any('/origin-source-preview/' in r['postimage']['path'] for r in p['inputs']['postimages'])
save('ACTUAL-ORIGIN-BINDING.json',dict(scope=p['scope'],status='PASS_EXISTING_ACTUAL_ORIGIN_BOUND_TO_EXACT_PROPOSAL',runtime_authority=None,source_adoption=ref(adoption_path),source_review=receipt['independent_source_review'],actual_producer_receipt=ref(receipt_path),actual_header=header,actual_origin_binding=ref(output/'ORIGIN-BINDING.json'),actual_Rust_environment=ref(output/'rust-environment.json'),actual_CMake_origin=ref(output/'f06_rt_sigreturn_origin.cmake'),predecessor_profile=ref(O/'PROFILE.SOURCE-ONLY.json'),successor_profile=ref(S/'PROFILE.SOURCE-ONLY.json'),replaced_source_preview_provenance_only=preview,commands_unchanged=True,eight_objects_unchanged=True,Rust113_source_closure_unchanged=True,Root33_lineage_modified=False,actual_new_producer_invocations=0,actual_new_materializations=0,actual_compilers=0,actual_native=0,canonical_writes=0))
save('ROOT-NEXT-ADMISSION-DATA.NOT-AUTHORITY.json',dict(scope=p['scope'],runtime_authority=None,status='EXACT_INPUTS_FOR_ROOT_FRESH_ADMISSION_NOT_A_GRANT',source_profile=ref(S/'PROFILE.SOURCE-ONLY.json'),source_export_template=ref(S/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json'),compiler_commands=ref(S/'EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json'),source_adoption=ref(adoption_path),actual_origin_binding=ref(S/'ACTUAL-ORIGIN-BINDING.json'),tools=tools,source_directory_manifest=ref(source_map_path),reuse_descriptor=ref(p['reuse_descriptor']),actual_F03_event2_HOST=p['qualified_F03_event2_independent_actual_HOST'],Root_next_steps=['Use this genuineheader-bound profile/export and byte-identical OCI-corrected tools as exact static inputs. No producer, HOST or accepted build replay.','Root rechecks actual current account/source/ownership and Root33-or-newer postretirement clearance; prior free04dd is not a new execution release. Bind current genuine records, fresh nonce/request/output/resource/holder and export authority without changing native priority or other packets.','Root performs existing exact publication/sourcefetch/independent execution review and holder protocol; run_build_only.execute takes only actual newly written reviewed grant. No new admission framework supplied here.','Four literal compiler/link argv are preserved in the attached command document. Existing runner precreates only header target under fresh writable/work; eight exact retained inputs and113Rust source map unchanged.','Actual producer return0/header268B is source-materialization proof only. New object/link/default/currentconsumer/native acceptance remains OPEN. Preserve every prior failure and original profile.'],actual_nonce=None,actual_request=None,actual_resource_authority=None,actual_holder=None,actual_output_root=None,actual_execution_review=None,actual_release=None,fixed_three_clock_cutoffs=p['fixed_three_clock_cutoffs'],aggregate_memory_budget_bytes=p['aggregate_memory_budget_bytes'],controls='CPU2-5/12GiB/noswap/512pids/networknone, oneheavy/permanent27:4/scratch21,7aggregatejobs/originalfreefloors; samecreditrun7f4af94a83b14cc08f97401f5891d965/57774.852125 cumulative debits and actualholds.'))
save('SOURCE-READY.json',dict(scope=p['scope'],status='CURRENT112_ACTUAL_ORIGIN_BOUND_PRIVATE_SUCCESSOR_READY_FOR_ROOT_ADMISSION_NOT_RELEASED',runtime_authority=None,profile=ref(S/'PROFILE.SOURCE-ONLY.json'),export=ref(S/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json'),actual_origin_binding=ref(S/'ACTUAL-ORIGIN-BINDING.json'),next_admission_data=ref(S/'ROOT-NEXT-ADMISSION-DATA.NOT-AUTHORITY.json'),tools=tools,commands=4,new_objects=3,retained_objects=8,closed_Rust_sources=113,new_materializations=0,new_compilers=0,canonical_writes=0))
print(json.dumps(dict(status='ACTUAL_ORIGIN_BOUND_SOURCE_SUCCESSOR_READY_NOT_RELEASED',profile=ref(S/'PROFILE.SOURCE-ONLY.json'),ready=ref(S/'SOURCE-READY.json'),new_executions=0)))
