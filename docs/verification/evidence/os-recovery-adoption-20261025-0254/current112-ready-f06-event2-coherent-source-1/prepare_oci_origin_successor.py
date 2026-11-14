"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Additive source-only correction: no producer, compiler, runtime or materialization.
"""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path
D=Path(__file__).resolve().parent
E=D.parent
S=D/'oci-origin-bind-correction-source-1'
S.mkdir(exist_ok=True)

def read(p):return json.loads(p.read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(name,b):
 p=S/name;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b and not p.is_symlink(),name
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(name,x):return write(name,json.dumps(x,indent=2)+'\n')
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
p=read(D/'PROFILE.SOURCE-ONLY.json')
export=read(D/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json')
oldbindings=copy.deepcopy(p['cohort_source_bindings'])
helper_refs=[ref(D/'candidate/scripts'/n) for n in ['derive_f06_origin.py','f06_origin_command_profile.json']]
arch=next(r for r in p['inputs']['postimages'] if r['relative']=='arch/x86_64/kernel/syscall.c')
header=next(r for r in p['inputs']['postimages'] if r['relative']=='kernel/rust/f06-origin/f06_rt_sigreturn_origin.h')
removed=[r for r in p['inputs']['postimages'] if r['relative'].startswith('scripts/')]
assert len(removed)==2
source_root=Path(p['inputs']['source6153'])
assert (source_root/'scripts').is_dir()
observed=[]
for row in removed:
 target=source_root/row['relative'];assert not target.exists() and not target.is_symlink()
 observed.append(dict(container_target=row['container_destination'],underlying_readonly_source_path=str(target),underlying_leaf_exists=False,disposition='Remove unnecessary compile-time OCI mount; use exact HOST source producer input before the four-command container; canonical CMake adoption stays unchanged.'))
p['inputs']['postimages']=[r for r in p['inputs']['postimages'] if r not in removed]
p['cohort_source_bindings']=[r for r in oldbindings if r['relative'] not in {v['relative'] for v in removed}]
p['status']='CURRENT112_PRIVATE_SOURCE_OCI_TARGET_SUCCESSOR_NOT_ADOPTED_NOT_RELEASED'
actualhost=E/'m14-f03-event-provider-bridges-next-source-1/independent-source-profile-review-1/INDEPENDENT-ACTUAL-HOST-ACCEPTANCE.json'
assert ref(actualhost)['sha256']=='a731fa32939d9f275e3adc4f63b5e2a5598fe64652227be0fe852a5c60e915ff'
newoutput=S/'ROOT-ORIGIN-PRODUCER-OUTPUT-1'
assert not newoutput.exists()
command=['/home/holden/anaconda3/bin/python3','-I','-B',helper_refs[0]['path'],'--profile',helper_refs[1]['path'],'--source',arch['postimage']['path'],'--output',str(newoutput)]
producer_contract=dict(scope=p['scope'],runtime_authority=None,status='PROPOSED_LITERAL_HOST_SOURCE_PRODUCER_NOT_EXECUTED',cwd='/home/holden/mckernel',argv=command,helpers=helper_refs,architecture_source=arch['postimage'],expected_output_root=str(newoutput),required_output_precondition='Root verifies output path absent, actual current source/account/ownership controls, then invokes exact source producer once under its authority; no compiler or SDK command.',expected_generated_header=dict(path=str(newoutput/'f06_rt_sigreturn_origin.h'),bytes=header['postimage']['bytes'],sha256=header['postimage']['sha256']),expected_origin_utf8='/src/arch/x86_64/kernel/syscall.c',expected_origin_bytes_with_nul=list(b'/src/arch/x86_64/kernel/syscall.c\0'),actual_invocations=0,actual_outputs=None,Root_after_producer=['Authenticate actual producer/header bytes and command/context; preserve failure without replay.','Rebind header postimage and matching cohort/export entries from source preview to genuine generated output; actual profile/publication/review must include that new reference.','The exact archargv and Rust env must equal the bound origin-command profile; four compiler/link commands unchanged.','Canonical future configure uses retained CMake script/profile paths; these two source files remain Root adoption inputs, with no OCI bind needed in this no-configure build.'])
save('LITERAL-ORIGIN-PRODUCER.NOT-GRANTED.json',producer_contract)
p['origin_source_materialization']=dict(runtime_authority=None,contract=ref(S/'LITERAL-ORIGIN-PRODUCER.NOT-GRANTED.json'),source_only=True,actual_producer_receipt=None,actual_generated_header=None,canonical_adoption_inputs=removed,compiler_OCI_mounts_for_helpers=0)
p['qualified_F03_event2_independent_actual_HOST']=ref(actualhost)
new_obligations=[]
for old in p['producer_contract']['postbuild_required']:
 replacements={
  'only two original panic imports removed':'Preserve exact accepted CURRENT111 panic/import closure; bind any actual CURRENT112 import delta explicitly.',
  'new syscall/process Rust symbol ownership and ABI/function checks at selected cohort scope':'Fresh fullRust/kernelC/archC ownership and ABI checks; retained actual CURRENT111 processa4309 remains unchanged.',
  'Prepublished ten-selector actual symbol/import/source and warning acceptance inputs':'Preserve original ten-selector gate at its exact inherited scope and bind the new F03event2/F06allocfree2 selectors, source/import/ABI and warning predicates.',
  'Exact F03 three original C callbacks absent and genuine Rust definitions unique with original CULong/CInt ABI, enable_perf and final provider calls/arguments preserved':'Preserve accepted inherited F03counter3 Rust ownership/ABI; prove new eventsetperiod/update2 C absence and genuine unique Rust definitions with original pointer/CULong/CInt ABI and enable_perf.',
  'Exact runqueue208/26words readonly min8alignment Rust ownership, no hidden table relocations, absence from fresh processC and positive final consumer pointers/offset semantics':'Reprove new fullRust/finalimage runqueue208/26words readonly/min8alignment/relocations and positive consumers against unchanged retained actual CURRENT111 processa4309; no fresh processC is produced.',
  'Qualified F03event2 independent actualHOST acceptance required before Root source adoption/release; no HOST replay.':'F03event2 independent actualHOST acceptance a731fa32939d9f275e3adc4f63b5e2a5598fe64652227be0fe852a5c60e915ff bound; no HOST replay. Root source adoption/release remain separate.',
 }
 new_obligations.append(replacements.get(old,old))
p['producer_contract']['postbuild_required']=new_obligations
save('PROFILE.SOURCE-ONLY.json',p)
# Retain source directory snapshots and reuse descriptor, all four literal argv unchanged.
assert p['exact_commands']==read(D/'PROFILE.SOURCE-ONLY.json')['exact_commands']
assert p['inputs']['objects']==read(D/'PROFILE.SOURCE-ONLY.json')['inputs']['objects']
runner=(D/'run_build_only.py').read_text()
needle="    build=output/'work/output/build';(build/'kernel/rust').mkdir(mode=0o700,parents=True)\n"
insertion="""    # Exact new header bind target lies under fresh writable /work, never /src.
    origin_target=build/'kernel/rust/f06-origin/f06_rt_sigreturn_origin.h'
    origin_target.parent.mkdir(mode=0o700)
    require(not os.path.lexists(origin_target),'fresh exact origin header bind target')
    origin_target.touch(mode=0o400,exist_ok=False)
"""
runner=once(runner,needle,needle+insertion)
tools=[]
for name,text in [('run_build_only.py',runner)]+[(n,(D/n).read_text()) for n in ['build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']]:
 ast.parse(text,filename=name)
 path=write(name,text);delta=write('tool-diffs/'+name+'.diff',''.join(difflib.unified_diff((D/name).read_text().splitlines(keepends=True),text.splitlines(keepends=True),fromfile='CURRENT112/'+name,tofile='CURRENT112-OCI/'+name)))
 tools.append(dict(name=name,predecessor=ref(D/name),successor=ref(path),diff=ref(delta)))
for helper in helper_refs:ast.parse(Path(helper['path']).read_text(),filename=helper['path']) if helper['path'].endswith('.py') else None
export['status']='CURRENT112_OCI_SUCCESSOR_TEMPLATE_NOT_AUTHORITY'
export['qualified_readonly_files']=[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in p['inputs']['postimages']]+[r['snapshot'] for r in read(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')['files']]
save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
plan=read(D/'EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json');plan['source_profile']=ref(S/'PROFILE.SOURCE-ONLY.json');plan['producer_contract']=p['producer_contract']
save('EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json',plan)
save('OCI-TARGET-READINESS.SOURCE-ONLY.json',dict(scope=p['scope'],runtime_authority=None,status='EXACT_SOURCE_MOUNT_CORRECTION_NOT_RUNTIME_QUALIFIED',predecessor_profile=ref(D/'PROFILE.SOURCE-ONLY.json'),readonly_source_root=str(source_root),source_observations=observed,origin_header=dict(container_target=header['container_destination'],underlying_mount='/work writable fresh output/work bind',exact_target_preparation=insertion,readonly_nested_mount=header['postimage'],fresh_parent_mkdir=True,fresh_leaf_touch=True,source6153_mutations=0),compiler_commands_unchanged=True,eight_retained_inputs_unchanged=True,Root32_lineage_modified=False,actual_Docker=0,actual_producer=0,actual_materializations=0,actual_tests=0,canonical_mutations=0,limitations='Static mount-layout resolution only; exact Docker execution needs fresh Root admission/review. Header preview must be replaced with actual bound producer output before build release.'))
save('ROOT-NEXT-STEPS.NOT-AUTHORITY.json',dict(scope=p['scope'],runtime_authority=None,owner='/root',steps=['Review this finite successor and bind actual F03event2 HOST a731fa32; preserve original qualified union/adoption inputs.', 'Root invokes LITERAL-ORIGIN-PRODUCER.NOT-GRANTED argv once after fresh checks, preserving output and receipt. No compiler or OCI operation is in that invocation.', 'Bind genuine generated header reference/receipt into successor profile/export/cohort and independently reviewed actual publication; source preview is not generated-runtime evidence.', 'Root adopts exact canonical candidate files/new leaf/producer/profile; source-only helpers remain separate adoption/materialization inputs, not unused /src OCI mounts.', 'Root grants reviewed four-command build with exact eight retained objects. Runner precreates only new header destination in fresh writable /work before readonly bind.', 'Bind actual fresh tuple and all truthful112 qualifier/currentconsumer obligations. No native/wholefile delta inferred.'],actual_nonce=None,actual_resource_authority=None,actual_holder=None,actual_output_root=None,actual_release=None,Root32_lineage='UNCHANGED; no files touched',fixed_three_clock_cutoffs=p['fixed_three_clock_cutoffs'],controls='Same account/debits/realholds; oneheavyCPU2-5/12GiB/noswap/512pids/networknone; permanent27:4/scratch21; aggregate7jobs/23259332608B; original freefloors unchanged.'))
save('SOURCE-READY.json',dict(scope=p['scope'],status='CURRENT112_MINIMAL_OCI_TARGET_SUCCESSOR_SOURCE_READY_NOT_RELEASED',runtime_authority=None,profile=ref(S/'PROFILE.SOURCE-ONLY.json'),predecessor_source_ready=ref(D/'SOURCE-READY.json'),readiness=ref(S/'OCI-TARGET-READINESS.SOURCE-ONLY.json'),literal_origin_producer=ref(S/'LITERAL-ORIGIN-PRODUCER.NOT-GRANTED.json'),actual_F03_event2_HOST=ref(actualhost),next_steps=ref(S/'ROOT-NEXT-STEPS.NOT-AUTHORITY.json'),tools=tools,commands=4,new_objects=3,retained_objects=8,closed_Rust_sources=113,actual_producer=0,actual_compiler=0,actual_workload=0,canonical_edits=0))
print(json.dumps(dict(status='SOURCE_ONLY_SUCCESSOR_READY',profile=ref(S/'PROFILE.SOURCE-ONLY.json'),ready=ref(S/'SOURCE-READY.json'),origin_producer=ref(S/'LITERAL-ORIGIN-PRODUCER.NOT-GRANTED.json'),actual_executions=0)))
