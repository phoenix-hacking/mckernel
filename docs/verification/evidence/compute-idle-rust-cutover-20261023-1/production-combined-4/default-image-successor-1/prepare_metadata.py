#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded metadata/controller preparation. Never materializes or compiles source.
"""
from pathlib import Path
import ast
import copy
import difflib
import hashlib
import json

R = Path('/home/holden/mckernel')
D = Path(__file__).resolve().parent
H = Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1')
B = H / 'production-combined-2'
N = H / 'production-combined-4/default-image-successor-1'
S = N / 'source-materialization-attempt-1'
E = R / 'docs/verification/evidence/compute-idle-rust-cutover-20261023-1'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
POST = {'arch/x86_64/kernel/memory.c': '25c13c856dff0a1219a316ac3cf38cbe40f79c16561813b98a408f8cb62c24ed',
        'kernel/rust/x86_memory_helpers.rs': '35664d46edaa3674d633b3c1ff96e85723fd21e5daf517d53c2438de35d5c4a3'}

def canonical(x): return (json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
def sha(x): return hashlib.sha256(x).hexdigest()
def ref(p):
    b=p.read_bytes();return dict(path=str(p), bytes=len(b), sha256=sha(b))
def write(p, b):
    with p.open('xb') as f: f.write(b)
def record(name, value): write(D/name, (json.dumps(value, indent=2, sort_keys=True)+'\n').encode())
def replace(text, before, after, count=1):
    assert text.count(before)==count, (before,text.count(before),count)
    return text.replace(before,after)
def controller(name, text, original):
    ast.parse(text)
    write(N/name,text.encode())
    write(D/(name+'.diff'), ''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile=str(B/'correction1'/name),tofile=str(N/name))).encode())
    return ref(N/name)

def main():
    old_path=B/'source-materialization-attempt-2/source-inputs.json'
    old_raw=old_path.read_bytes();base=json.loads(old_raw)
    assert sha(old_raw)==sha(canonical(base))=='9b86c84a92133678171b3e476560bcdfc99070f727b9c11c764de7092de8b88c'
    auth=E/'page-free-callback-4/CANONICAL-INTEGRATION.json';ab=auth.read_bytes();a=json.loads(ab)
    assert a['status']=='PASS_SOURCE_INTEGRATED' and a['postimages']==POST
    doc=copy.deepcopy(base);delta=[]
    for p,h in POST.items():
        assert sha((R/p).read_bytes())==h
        delta.append(dict(path=p,before_sha256=base['repository_files'][p],after_sha256=h))
        doc['repository_files'][p]=doc['materialized_repository_files'][p]=h
    derivation=dict(base_manifest_canonical_sha256=sha(old_raw),base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=sha(ab),latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay'])
    doc['source_derivative_sha256']=sha(canonical(derivation));doc['latest_memory_callback_overlay']=derivation
    materialization={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')}
    doc['materialization_sha256']=sha(canonical(materialization));mh=sha(canonical(doc))
    assert [p for p in base['repository_files'] if base['repository_files'][p]!=doc['repository_files'][p]]==list(POST)
    source=(E/'production-combined-2/materialize_generated_candidate2.py').read_text()
    source=replace(source,str(B/'source-materialization-attempt-2'),str(S))
    source=replace(source,str(H/'memory-combined-preparation-1'),str(B/'source-materialization-attempt-2'))
    source=replace(source,'phys-to-virt-callback-1/CANONICAL-INTEGRATION.json','page-free-callback-4/CANONICAL-INTEGRATION.json')
    source=replace(source,'db4f6a3b25f5b483cc2a34cc06efa374396cfdadfb074162e81aadeaf02e9240',sha(old_raw))
    for p,h in POST.items(): source=replace(source,base['repository_files'][p],h)
    source=replace(source,"authority['decision'] == 'PASS_M14_CALLBACK_SOURCE_AND_SELECTED_ABI_LINK'\n         and {path:row['sha256'] for path,row in authority['postimages'].items()} == POST", "authority['status'] == 'PASS_SOURCE_INTEGRATED' and authority['postimages'] == POST")
    ast.parse(source);write(D/'materialize_source.py',source.encode())
    old_op=json.loads((E/'production-combined-2/correction1/EXACT-PRODUCTION-OPERATION.CORRECTION1.PROPOSED.json').read_text())
    pins=old_op['production_sources'];outputs={}
    name='native_rust_exact_build_offline.py';raw=Path(pins[name]['path']).read_text();assert sha(raw.encode())==pins[name]['sha256']
    outputs[name]=controller(name,replace(raw,sha(old_raw),mh),raw)
    name='native_rust_exact_mckernel_image_offline.py';raw=Path(pins[name]['path']).read_text();assert sha(raw.encode())==pins[name]['sha256'];text=replace(raw,pins['native_rust_exact_build_offline.py']['sha256'],outputs['native_rust_exact_build_offline.py']['sha256'])
    for p,h in POST.items(): text=replace(text,base['repository_files'][p],h)
    text=replace(text,"M14_MEMORY_IMPORTS = ('x86_clear_old_action_bridge', 'x86_clear_phys_to_virt_bridge')", "M14_MEMORY_IMPORTS = ('x86_clear_old_action_bridge', 'x86_clear_phys_to_virt_bridge',\n                      'x86_clear_page_unmap_bridge', 'x86_clear_free_pages_user_bridge')")
    # Preserve accepted correction1 _run_process body and 1MiB site cap exactly.
    outputs[name]=controller(name,text,raw)
    name='native_rust_exact_mckernel_image_container_owner.py';raw=Path(pins[name]['path']).read_text();assert sha(raw.encode())==pins[name]['sha256'];text=raw
    for n in outputs:
        text=replace(text,pins[n]['sha256'],outputs[n]['sha256'])
    text=replace(text,str(B/'correction1/native_rust_exact_build_offline.py'),str(N/'native_rust_exact_build_offline.py'))
    old_attempt=B/'correction1/pinned-full-image-attempt-1';new_attempt=N/'pinned-full-image-attempt-1'
    text=replace(text,str(old_attempt/'common-exclusion.json'),str(new_attempt/'common-exclusion.json'))
    text=replace(text,'LIMITS = {', 'RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(('+repr(str(old_attempt/'common-exclusion.json'))+',))\n\nLIMITS = {')
    outputs[name]=controller(name,text,raw)
    record('SOURCE-BINDING-DELTA.json',dict(scope=SCOPE,base_manifest=ref(old_path),canonical_integration=ref(auth),changed_source_files=delta,preserved_idle3={p:base['repository_files'][p] for p in ('kernel/process.c','kernel/rust/sched_helpers.rs','kernel/include/sched_helpers.h')},predicted_source_manifest_sha256=mh,predicted_source_manifest_bytes=len(canonical(doc)),predicted_source_derivative_sha256=doc['source_derivative_sha256'],predicted_materialization_sha256=doc['materialization_sha256'],source_entries=6959,materialized_source=None,materialization_result=None,controller_successors=outputs,gate_extension='Existing selected preprocessing/import/relocation and unique Rust/final export gates now cover both additional memory callbacks; existing 1MiB cap/global guard unchanged.',all_other_source_references_preserved=True))
    record('OPERATION.PROPOSED.json',dict(scope=SCOPE,status='PREPARED_NOT_RELEASED_NOT_MATERIALIZED',predecessor_operation=ref(E/'production-combined-2/correction1/EXACT-PRODUCTION-OPERATION.CORRECTION1.PROPOSED.json'),profile=old_op['profile'],pinned_inner_commands=old_op['pinned_inner_commands'],production_sources=outputs,source_manifest=None,source_root=None,static_request=None,final_request=None,final_image=None,native=None,execution_released=False,next_preparation=dict(purpose=SCOPE+' Materialize exact finite successor once after ordinary grant; preserve source/journal/failure bytes.',argv=['/usr/bin/taskset','-c','0','/usr/bin/python3','-I','-B',str(D/'materialize_source.py')],grant_required=True,preconditions=[str(S)+' exists empty mode0700','positive predecessor/aggregate reconciliation; no competing heavy workload'],profile=dict(cpu=0,jobs=1,as_bytes=2<<30,cpu_seconds=30,wall_seconds=35,termination_grace_seconds=3,fsize_bytes=32<<20,nofile=256,core=0,host_growth_max_bytes=256<<20,capture_extra_bytes=16<<20,host_floor_bytes=16<<30,scratch_floor_bytes=12<<30,scratch_writes=False)),followup_preparation='After successful materialization: bind predicted manifest actual bytes; mechanically advance existing gitlink supplement base_manifest_sha256; incrementally derive accepted 26,524,779-byte compact static request with exact new source/manifest/controller/gitlink pins and fresh namespace. Preserve every other inventory/toolchain/null admission field. Do not execute old owner or static request unchanged.', eventual_outer_argv=['/home/holden/anaconda3/bin/python3','-I','-B',outputs['native_rust_exact_mckernel_image_container_owner.py']['path'],str(N/'image-request.FINAL.json')],required_root_gates=['focused independent source/profile review','fetched publication and source acceptance','positive physical predecessor retirement and repaired observer','fresh disk/loop/backing identity and full sparse-gap capacity','aggregate single-heavy grant and one-shot execution release'],failure_family_history=['Original materialization SourceFSIZE8MiB EFBIG retained; correction32MiB accepted. Do not repeat 8MiB.','Original observer32MiB versus global1MiB rejected; accepted correction1 sitecap1MiB preserved. Any recurrence requires expert escalation; never widen guard.'],acceptance_credit=False))
    print(json.dumps(dict(status='PASS_BOUNDED_PREPARATION_ONLY',predicted_manifest_sha256=mh,source_copy_or_compile=False)))

if __name__=='__main__':main()
