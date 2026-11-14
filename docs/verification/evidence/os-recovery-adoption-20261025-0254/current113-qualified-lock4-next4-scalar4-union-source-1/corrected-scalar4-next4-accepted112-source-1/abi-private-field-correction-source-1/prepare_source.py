"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded E0616 ABI witness correction, private source/profile only.
"""
import ast,copy,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;CAND=D.parent;E=D.parents[2];ROOT=E.parents[3]
A=E/'ROOT-CURRENT113-CORRECTED-SCALAR4-NEXT4-BUILD-ADMISSION-1'
A112=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
LEAF='f06_clone_ptrace_provider_abi.rs'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return write(n,json.dumps(x,indent=2)+'\n')
old=read(A/'PROFILE.SOURCE-ONLY.json');oldmap_path=auth(old['inputs']['source_directory_exports'][0]['manifest']);oldmap=read(oldmap_path)
prior={r['relative']:r for r in oldmap['files']};assert len(prior)==118
canonical=ROOT/'kernel/rust'/LEAF
before=auth(prior[LEAF]['snapshot']).read_text();assert ref(canonical)['sha256']==prior[LEAF]['snapshot']['sha256']
illegal='    assert!(core::mem::offset_of!(McsRwlockNodeIrqsave, irqsave) == 0);\n'
comment='    // The irqsave offset-zero witness is asserted unconditionally in\n    // lock_helpers.rs, inside the defining module\'s existing const block.\n'
assert before.count(illegal)==1
after=before.replace(illegal,comment,1)
assert after.replace(comment,illegal,1)==before
# Exact same predicate already exists legally within its defining module, unchanged.
lockfile=ROOT/'kernel/rust/lock_helpers.rs';locktext=lockfile.read_text();predicate='    assert!(offset_of!(McsRwlockNodeIrqsave, irqsave) == 0);'
assert locktext.count(predicate)==1
map112=read(auth(read(A112/'PROFILE.SOURCE-ONLY.json')['inputs']['source_directory_exports'][0]['manifest']))
lock112=next(r for r in map112['files'] if r['relative']=='lock_helpers.rs')
assert ref(lockfile)['sha256']==lock112['snapshot']['sha256']
start=locktext.index('const _: () = {');end=locktext.index('\n};',start)+3
block=locktext[start:end];assert predicate in block and '#[cfg' not in block
line=locktext[:locktext.index(predicate)].count('\n')+1;assert line==59
write('preimages/'+LEAF,before);write('candidate/kernel/rust/'+LEAF,after)
patch=write('f06_clone_ptrace_provider_abi.rs.patch',''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/kernel/rust/'+LEAF,tofile='b/kernel/rust/'+LEAF)))
write('defining-module-existing-const-witness.rs.inc',block+'\n')
rows=[]
for r in oldmap['files']:
 oldpath=auth(r['snapshot']);path=write('rust-subtree/'+r['relative'],after if r['relative']==LEAF else oldpath.read_bytes())
 row=copy.deepcopy(r);row['snapshot']=ref(path);row['predecessor_snapshot']=r['snapshot'];row['kind']='bounded private-field duplicate witness correction' if r['relative']==LEAF else 'unchanged exact failed113 source'
 rows.append(row)
assert {r['relative'] for r in rows if r['snapshot']['sha256']!=r['predecessor_snapshot']['sha256']}=={LEAF}
newmap=copy.deepcopy(oldmap);newmap.update(export_root=str(D/'rust-subtree'),files=rows,total_bytes=sum(r['snapshot']['bytes'] for r in rows),new_leaf_files=[],predecessor_manifest=ref(oldmap_path),original_source_mutations=0)
save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',newmap)
p=copy.deepcopy(old);p.update(status='CURRENT113_BOUNDED_E0616_PRIVATE_FIELD_CORRECTION_SOURCE_ONLY_NOT_ADOPTED_NOT_RELEASED',runtime_authority=None)
for k in ['request_sha256','native_custody_clearance','actual_nonce','actual_root_adoption','actual_execution_review','actual_resource_authority','actual_output_root','actual_holder']:p[k]=None
p['inputs']['source_directory_exports']=[dict(host_path=str(D/'rust-subtree'),container_destination='/src/kernel/rust',readonly=True,manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
p['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in p['inputs']['postimages']]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in rows]
p['source_preparation_current_context']=dict(runtime_authority=None,status='ROOT37_LEDGER_AND_FAILED113_POSTJOIN_FREE_PROOF_PENDING_ROOT_BINDING',current_nonce_ledger=None,current_native_custody_clearance=None,predecessor_failed_source_profile=ref(A/'PROFILE.SOURCE-ONLY.json'))
origin=p['origin_source_materialization'];assert origin['actual_producer_receipt']['sha256']=='2c419c6405deef8d6e8c2479e57f88884e34a84fec300e0aff5311ea04b944fb'
for k in ['actual_producer_receipt','actual_generated_header','actual_origin_binding','actual_Rust_environment','actual_CMake_origin']:auth(origin[k])
context=read(origin['actual_origin_binding']['path']);assert context['command']==p['exact_commands'][2]
assert context['source_sha256']==next(r['postimage']['sha256'] for r in p['inputs']['postimages'] if r['relative']=='arch/x86_64/kernel/syscall.c')
assert p['exact_commands']==old['exact_commands'] and p['inputs']['objects']==old['inputs']['objects']
assert len(p['exact_commands'])==4 and sum(not r['replace'] for r in p['inputs']['objects'])==8
p['reuse_descriptor']=str(D/'FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json')
reuse=read(Path(old['reuse_descriptor']));reuse['bounded_abi_correction']=dict(runtime_authority=None,leaf=LEAF,leaf_source=ref(D/'candidate/kernel/rust'/LEAF),runtime_bodies_changed=False,origin_replayed=False)
save('FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json',reuse)
p['producer_contract']['postbuild_required'].append('Retain defining-module unconditional irqsave offset-zero proof at lock_helpers.rs59 unchanged; only illegal duplicate cross-module E0616 assertion replaced by comment. All other typed/size/alignment witnesses remain exact. One bounded correction, escalate if repeated compiler failure.')
save('PROFILE.SOURCE-ONLY.json',p)
export=read(A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json');export.update(status='ABI_CORRECTION_EXPORT_TEMPLATE_NOT_AUTHORITY',author=None,decision=None,request_sha256=None)
export['qualified_readonly_files']=[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in p['inputs']['postimages']]+[r['snapshot'] for r in rows]
save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
plan=read(CAND/'final-scope-source-1/EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json');plan.update(commands=p['exact_commands'],source_profile=ref(D/'PROFILE.SOURCE-ONLY.json'),producer_contract=p['producer_contract'])
save('EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json',plan)
tools=[]
for n in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 raw=(A/n).read_bytes();ast.parse(raw,filename=n);dest=write(n,raw);tools.append(dict(name=n,predecessor=ref(A/n),successor=ref(dest),byte_identical=True))
result_path=A/'OUTPUT/work/evidence/worker-result.json';stderr_path=A/'OUTPUT/work/evidence/00.stderr';result=read(result_path)
assert len(result['commands'])==1 and result['commands'][0]['index']==0 and result['commands'][0]['returncode']==1
assert result['commands'][0]['CPU_seconds']==3.110836 and result['commands'][0]['maximum_child_RSS_KiB']==419364
assert 'error[E0616]' in stderr_path.read_text() and 'irqsave' in stderr_path.read_text()
wall=result['commands'][0]['finished_at_epoch']-result['commands'][0]['started_at_epoch'];assert abs(wall-3.113695)<0.000001
save('ORIGINAL-FAILURE-AND-ONE-CORRECTION.json',dict(scope=SCOPE,runtime_authority=None,family='Rust E0616 duplicate private irqsave offset assertion',original_worker_result=ref(result_path),original_stderr=ref(stderr_path),first_failed_command_index=0,returncode=1,CPU_seconds=3.110836,maximum_RSS_KiB=419364,wall_seconds_recorded=wall,wall_seconds_rounded=3.113695,passed_compiler_prefix=0,remaining_commands_unrun=3,required_next_commands=4,correction_count=1,bounded_correction='Remove only illegal duplicate cross-module assertion and replace explanatory comment; no type visibility/layout/runtime/body/otherABI witness change.',on_repeated_failure='Escalate to expert; no automatic further candidate/replay.',actual_correction_compiler_invocations=0))
save('EXACT-EXISTING-ABI-WITNESS.json',dict(scope=SCOPE,runtime_authority=None,defining_source=ref(lockfile),accepted_current112_snapshot=lock112['snapshot'],line=59,predicate=predicate.strip(),same_semantic_predicate_removed_from_illegal_scope=illegal.strip(),existing_const_block=ref(D/'defining-module-existing-const-witness.rs.inc'),unconditional_in_defining_module=True,private_field_visibility_unchanged=True,all_other_leaf_witnesses_unchanged=True,runtime_bodies_changed=False,source_only=True))
save('ROOT-ADOPTION-REBIND.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,required_Root_action='Adopt only exact corrected leaf after independent source review; retain original113 failedsource receipts. Rebind actual source-adoption chain and sourcepublication to this new118map/profile.',canonical_path=str(canonical),canonical_preimage=ref(canonical),private_postimage=ref(D/'candidate/kernel/rust'/LEAF),patch=ref(patch),existing_defining_witness=ref(D/'EXACT-EXISTING-ABI-WITNESS.json'),actual_Root_adoption=None,actual_source_publication=None,genuine_origin_reused=origin['actual_producer_receipt'],architecture_source_unchanged=True,architecture_argv_unchanged=True,actual_origin_producer_replayed=False,actual_next_nonce=None,actual_current_ledger=None,actual_postjoin_free_proof=None,actual_resource_authority=None,actual_holder=None,actual_output_root=None,actual_execution_review=None,actual_release=None))
save('ROOT-NEXT-STEPS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,steps=['Independently review tiny leaf patch and exact unchanged lock_helpers59 witness; Root alone adopts corrected leaf.', 'Finish actual failed113 owner/container retirement and independent positive currentfree; bind Root37-or-later exact ledger/account/source/ownership/resource, freshnonce/output/holder/publication/review+grant. No old release revived.', 'Reuse exact genuine113origin2c419/header/env and unchanged architecture source/argv; no producer replay. Keep all eight retained object refs.', 'After actual reviewed one-heavy admission, run all four original compiler/link commands: corrected failed Rust compile plus three never-run suffix commands. No passed-prefix claim.', 'Preserve firstE0616/fullstderr/result and all failedsources. This is the one bounded correction; escalate on repeated failure. Production/default/native/wholefile acceptance remains OPEN.'],commands=4,failed_command_to_recompile=0,unrun_suffix=[1,2,3],passed_prefix=0,actual_compiler=0,actual_queries=0,canonical_or_Git_writes=0,fixed_three_clock_cutoffs=p['fixed_three_clock_cutoffs']))
save('SOURCE-READY.json',dict(scope=SCOPE,status='ONE_BOUNDED_E0616_ABI_DUPLICATE_WITNESS_CORRECTION_SOURCE_READY_NOT_ADOPTED_NOT_RELEASED',runtime_authority=None,profile=ref(D/'PROFILE.SOURCE-ONLY.json'),source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),tiny_patch=ref(patch),existing_witness=ref(D/'EXACT-EXISTING-ABI-WITNESS.json'),first_failure=ref(D/'ORIGINAL-FAILURE-AND-ONE-CORRECTION.json'),Root_adoption_rebind=ref(D/'ROOT-ADOPTION-REBIND.NOT-AUTHORITY.json'),next_steps=ref(D/'ROOT-NEXT-STEPS.NOT-AUTHORITY.json'),tools=tools,commands=4,new_objects=3,retained_objects=8,Rust_sources=118,passed_prefix=0,genuine_origin_reused=origin['actual_producer_receipt'],actual_compilers=0,actual_queries=0,canonical_or_Git_writes=0))
print(json.dumps(dict(status='BOUNDED_CORRECTION_SOURCE_ONLY_READY',ready=ref(D/'SOURCE-READY.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),leaf=ref(D/'candidate/kernel/rust'/LEAF))))
