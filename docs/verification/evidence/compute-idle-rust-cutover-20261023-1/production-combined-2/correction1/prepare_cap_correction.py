#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One private1MiB callsite correction; preserve the existing runner admission guard.
"""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import os

D=Path(__file__).resolve().parent
P=D.parent
BASE=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2')
H=BASE/'correction1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def ref(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def save(name,before,after):
    ast.parse(after)
    with (H/name).open('x') as f:f.write(after)
    with (D/(name+'.diff')).open('x') as f:f.write(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=str(BASE/name),tofile=str(H/name))))
    return ref(H/name)

def main():
    old_driver=BASE/'native_rust_exact_mckernel_image_offline.py'
    assert ref(old_driver)['sha256']=='46b426530bbde4054d19af52fc815aece237e20b84031a2594c1575a0dbe5942'
    old=old_driver.read_text();new=replace(old,"row['phase'], output_fsize=32 << 20)","row['phase'], output_fsize=1 << 20)")
    before_ast=ast.parse(old);after_ast=ast.parse(new)
    a=next(n for n in before_ast.body if isinstance(n,ast.FunctionDef) and n.name=='_run_process')
    b=next(n for n in after_ast.body if isinstance(n,ast.FunctionDef) and n.name=='_run_process')
    assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
    driver=save('native_rust_exact_mckernel_image_offline.py',old,new)
    provenance=BASE/'native_rust_exact_build_offline.py'
    assert ref(provenance)['sha256']=='1be3a017e2ae47a0d1ecfcd4e1d22d7d8d569808e495d2b6d055c851d0582ae2'
    with (H/provenance.name).open('xb') as f:f.write(provenance.read_bytes())
    old_owner=BASE/'native_rust_exact_mckernel_image_container_owner.py'
    assert ref(old_owner)['sha256']=='e95e41a3fe7d3abadf996b16414312cb943627773ce78bf50df2c9039009d4ce'
    before=old_owner.read_text();owner=replace(before,'46b426530bbde4054d19af52fc815aece237e20b84031a2594c1575a0dbe5942',driver['sha256'])
    owner=replace(owner,str(provenance),str(H/provenance.name))
    old_attempt=BASE/'pinned-full-image-attempt-1';attempt=H/'pinned-full-image-attempt-1'
    owner=replace(owner,str(old_attempt/'common-exclusion.json'),str(attempt/'common-exclusion.json'))
    owner=replace(owner,'LIMITS = {',"RETIRED_COMMON_EXCLUSIONS = RETIRED_COMMON_EXCLUSIONS | frozenset(("+repr(str(old_attempt/'common-exclusion.json'))+",))\n\nLIMITS = {")
    owner_ref=save(old_owner.name,before,owner)
    request=json.loads((BASE/'image-request.STATIC-DATA.expert-compact1.json').read_text())
    request['driver_path']=driver['path'];request['driver_sha256']=driver['sha256']
    request['provenance_path']=str(H/provenance.name)
    for key in ('work_root','output_root','evidence_root','owner_evidence_root','attempt_root','lease_path','common_exclusion_path'):
        assert request[key].startswith(str(old_attempt)+'/');request[key]=str(attempt)+request[key][len(str(old_attempt)):]
    request['memory_allocation_roots']=[str(attempt)+p[len(str(old_attempt)):] if p.startswith(str(old_attempt)+'/') else p for p in request['memory_allocation_roots']]
    encoded=(json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    assert len(encoded)<=32<<20
    path=H/'image-request.STATIC-DATA.json'
    with path.open('xb') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
    assert path.read_bytes()==encoded and json.loads(encoded)==request
    operation=json.loads((P/'EXACT-PRODUCTION-OPERATION.PROPOSED.json').read_text())
    operation['status']='ONE_BOUNDED_M14_CAPTURE_CAP_CORRECTION_PENDING_ACTUAL_BODY_FIXTURE_AND_REREVIEW'
    operation['outer_argv'][-2:]=[owner_ref['path'],str(H/'image-request.FINAL.json')]
    operation['static_request']=ref(path);operation['fresh_output']=str(attempt)
    operation['production_sources']['native_rust_exact_mckernel_image_offline.py']=driver
    operation['production_sources']['native_rust_exact_mckernel_image_container_owner.py']=owner_ref
    operation['production_sources']['native_rust_exact_build_offline.py']=ref(H/provenance.name)
    operation['cap_correction']='Only _m14_observe output_fsize32MiB→1MiB. Original _run_process body/1MiB guard and every unrelated cap/gate unchanged. Any future actual output over1MiB fails closed; no automatic widening.'
    operation['predecessor_frozen_operation']=ref(P/'EXACT-PRODUCTION-OPERATION.PROPOSED.json')
    write(D/'EXACT-PRODUCTION-OPERATION.CORRECTION1.PROPOSED.json',operation)
    expected_paths=[
      Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/memory-combined-preparation-1/ordinary-selected-memory-tuple-attempt-1/selected-memory-preprocess.stdout'),
      Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/memory-combined-preparation-1/ordinary-selected-memory-tuple-attempt-1/selected-memory-relocations.stdout'),
      Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/evidence/rust-object-symbols.txt'),
      Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/evidence/symbols.txt')]
    write(D/'CAP-CORRECTION-SOURCE-BINDING.json',dict(scope=SCOPE,old_driver=ref(old_driver),new_driver=driver,
        provenance=ref(H/provenance.name),new_owner=owner_ref,static_request=ref(path),
        runner_body_AST_identical=True,global_max_capture_bytes=1<<20,
        expected_existing_output_sizes=[dict(path=str(p),bytes=p.stat().st_size,below1MiB=p.stat().st_size<1<<20) for p in expected_paths],
        expected_new_output='Existing memory PP286557B, memory relocs331425B, whole final/Rust symbol inventories230346/186705B fit. Baseline actual process relocation observation is included in the actual-body fixture. No claim that unobserved future output is guaranteed; larger output fails under unchanged cap.',
        canonical_or_frozen_sources_changed=False,builds=0,root_Docker_guests=0,
        one_bounded_cap_correction=True,second_actual_invariant_failure_stop=True))

if __name__=='__main__':main()
