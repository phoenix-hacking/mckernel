"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source-only CURRENT111 derivation. No admission, execution or publication.
"""
from pathlib import Path
import ast
import copy
import difflib
import hashlib
import json

D = Path(__file__).resolve().parent
E = D.parent
ROOT = E.parents[3]
A = E/'ROOT-CURRENT110-HOST19-BUILD-ADMISSION-1'
P = E/'current110-host19-production-preparation-source-1'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
ADOPTIONS = [E/'m14-f03-next-supported-body-new12h-1/ROOT-CANONICAL-SOURCE-ADOPTION.json', E/'m14-f02-next-readonly-data-new12h-1/ROOT-CANONICAL-SOURCE-ADOPTION.json']
ACCEPTANCE = A/'independent-final-consumer-review-1/DEFAULT-ARTIFACT-REVIEW.json'

def read(p): return json.loads(p.read_text())
def ref(p):
    p=Path(p); raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(name, raw):
    p=D/name; p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        assert p.read_bytes()==raw and not p.is_symlink(), 'frozen own output differs: '+name
    else:
        with p.open('xb') as stream: stream.write(raw)
        p.chmod(0o400)
    return p
def save(name,x): return write(name,(json.dumps(x,indent=2)+'\n').encode())
def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b,1)

old=read(A/'PROFILE.SOURCE-ONLY.json'); acceptance=read(ACCEPTANCE)
assert acceptance['decision']=='PASS_ACTUAL_CURRENT110_DEFAULT_SELECTED_ARTIFACT'
assert ref(A/'PROFILE.SOURCE-ONLY.json')==acceptance['profile']
assert acceptance['actual_commands']==5 and acceptance['exit_codes']==[0]*5
assert acceptance['tuple']['Rust']['sha256']=='e2c3032791bbd657a85629dd48ca86b3b93f3ef729305568031776d5674ad9d0'
assert acceptance['tuple']['image']['sha256']=='60e62f97ef48ecaf14174af1c5b75d7181969f439c1b45c618d6c16d4bc40d57'
for a in ADOPTIONS:
    for relative,digest in read(a)['postimages'].items():
        assert ref(ROOT/relative)['sha256']==digest,relative

oldmap_path=Path(old['inputs']['source_directory_exports'][0]['manifest']['path'])
oldmap=read(oldmap_path); prior={r['relative']:r for r in oldmap['files']}
assert len(prior)==112
actual={str(p.relative_to(ROOT/'kernel/rust')) for p in (ROOT/'kernel/rust').rglob('*') if p.is_file()}
excluded=actual-set(prior)
assert all('/__pycache__/' in p and p.endswith('.pyc') for p in excluded),excluded
assert set(prior)<=actual
rows=[]
for relative in sorted(prior):
    canonical=ROOT/'kernel/rust'/relative
    assert not canonical.is_symlink()
    snapshot=write('rust-subtree/'+relative,canonical.read_bytes())
    rows.append(dict(relative=relative,original=ref(canonical),snapshot=ref(snapshot),predecessor_snapshot=prior[relative]['snapshot'],kind='unchanged CURRENT110' if ref(snapshot)['sha256']==prior[relative]['snapshot']['sha256'] else 'Root adopted CURRENT111 successor'))
assert {r['relative'] for r in rows if r['kind']!='unchanged CURRENT110'}=={'sched_helpers.rs','syscall_policy.rs'}
source_map=dict(scope=SCOPE,runtime_authority=None,schema='mckernel.exact-kernel-rust-subtree-readonly.v1',base_source_root=old['inputs']['source6153']+'/kernel/rust',export_root=str(D/'rust-subtree'),container_destination='/src/kernel/rust',files=rows,total_bytes=sum(r['snapshot']['bytes'] for r in rows),new_leaf_files=[],no_symlinks=True,no_hardlinks=True,original_source_mutations=0,predecessor_manifest=ref(oldmap_path),excluded_generated_cache_preserved=[ref(ROOT/'kernel/rust'/p) for p in sorted(excluded)])
save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',source_map)
profile=copy.deepcopy(old)
profile.update(status='CURRENT111_COUNTER3_RUNQUEUE208_SOURCE_PREPARATION_NOT_RELEASED',runtime_authority=None)
for key in ['request_sha256','native_custody_clearance','actual_nonce','actual_root_adoption','actual_execution_review','actual_resource_authority','actual_output_root','actual_holder']:
    profile[key]=None
postimages=[]
for r in old['inputs']['postimages']:
    row=copy.deepcopy(r); canonical=ROOT/row['relative']
    row['postimage']=ref(write('candidate/'+row['relative'],canonical.read_bytes()))
    postimages.append(row)
assert {r['relative'] for r,o in zip(postimages,old['inputs']['postimages']) if r['postimage']['sha256']!=o['postimage']['sha256']}=={'kernel/CMakeLists.txt','kernel/process.c','kernel/syscall.c'}
profile['inputs']['postimages']=postimages
profile['inputs']['source_directory_exports']=[dict(host_path=str(D/'rust-subtree'),container_destination='/src/kernel/rust',readonly=True,manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
profile['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in postimages]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in rows]
producer=read(A/'OUTPUT/work/evidence/producer-contract.json')
outputs={}
for row in producer['commands']:
    r=row['output']; relative=Path(r['path']).relative_to('/work/output/build').as_posix()
    host=ref(A/'OUTPUT/work/output/build'/relative)
    assert host['sha256']==r['sha256'] and host['bytes']==r['bytes']
    outputs[relative]=host
arch='kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'
for row in profile['inputs']['objects']:
    if row['replace']:
        row['source']=outputs[row['build_relative']]
        row['retained_archive_member']=row['source']['path']
        row['action']='CURRENT110 predecessor provenance only; rebuild changed CURRENT111 object'
    if row['build_relative']==arch:
        row['replace']=False
        row['action']='Retain exact accepted CURRENT110 architecture syscall object; no source/selector change, no recompile'
        assert row['source']['sha256'].startswith('ce8f1ace')
    assert ref(row['source']['path'])==row['source']
for row in profile['inputs']['configuration']: assert ref(row['source']['path'])==row['source']
profile['inputs']['retained_count']=8;profile['inputs']['replaced_count']=3
commands=copy.deepcopy(old['exact_commands'])
commands.pop(3)
argv=commands[0]['argv']; idx=next(i for i,v in enumerate(argv) if v.startswith('--emit=obj='))
argv[idx:idx]=['--cfg','f03_perf_counter_control_bridges_selected_candidate']
argv=commands[2]['argv']; idx=next(i for i,v in enumerate(argv) if v.startswith('-I'))
argv[idx:idx]=['-DMCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES']
assert commands[1]==old['exact_commands'][1] and commands[3]==old['exact_commands'][4]
profile['exact_commands']=commands
contract=profile['producer_contract']
contract.update(source='Accepted CURRENT110 plus Root adopted F03 counter3/F02 runqueue208; four commands/three fresh objects/eight retained inputs',new_objects=[r['build_relative'] for r in profile['inputs']['objects'] if r['replace']],reused_objects=8,process_delta='Expected68->67 C OBJECT records: process_sched_runqueue_offsets208B/26words transfers to Rust under existing process_global_storage_candidate; verify actual symbol set and every final consumer. Preserve timer120B/idle116B/13 tracked lines.',expected_F03_C_functions=66,expected_F06_C_functions=25,expected_total_selected_C_functions=91,expected_current_cohort_Rust_function_exports=48,expected_process_OBJECT_records=67,expected_new_C_function_removals=['perf_counter_mask_check_bridge','perf_counter_start_bridge','perf_counter_stop_bridge'],expected_new_Rust_data=['process_sched_runqueue_offsets'],counts_are_unaccepted_expectations=True)
contract['postbuild_required']=[s.replace('four-object','three-object').replace('seven unchanged retained objects and four new objects','eight unchanged retained objects and three new objects') for s in contract['postbuild_required']]
contract['postbuild_required'] += ['Exact F03 three original C callbacks absent and genuine Rust definitions unique with original CULong/CInt ABI, enable_perf and final provider calls/arguments preserved','Exact runqueue208/26words readonly min8alignment Rust ownership, no hidden table relocations, absence from fresh processC and positive final consumer pointers/offset semantics','Independent current final-consumer supplement must reread timer120B/idle116B/logger/folded arguments and all other inherited consumers against this new image; retain original scripted OPEN/FAIL']
profile['reuse_descriptor']=str(D/'FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json')
save('FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json',dict(scope=SCOPE,runtime_authority=None,accepted_CURRENT110=ref(ACCEPTANCE),predecessor_profile=ref(A/'PROFILE.SOURCE-ONLY.json'),predecessor_producer=ref(A/'OUTPUT/work/evidence/producer-contract.json'),configuration=profile['inputs']['configuration'],objects=profile['inputs']['objects'],new_objects=contract['new_objects'],actual_commands=commands,source_view=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),configuration_reuse_not_fresh_configure=True,SDK21_recompiled=False,previous_commands_replayed=False))
save('PROFILE.SOURCE-ONLY.json',profile)
save('EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,deadline_epoch=profile['deadline_epoch'],fixed_three_clock_cutoffs=profile['fixed_three_clock_cutoffs'],commands=commands,source_profile=ref(D/'PROFILE.SOURCE-ONLY.json'),tool_files=read(A/'OUTPUT/plan.json')['tool_files'],producer_contract=contract))

# Preserve original custody/resource/account implementation; only cohort cardinality changes.
runner=(A/'run_build_only.py').read_text()
for a,b in [
 ('matching seven-object/four-replacement reuse descriptor','matching eight-object/three-replacement reuse descriptor'),
 ("'CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']","'mckernel.img']"),
 ("'/src/kernel/syscall.c','/src/arch/x86_64/kernel/syscall.c']","'/src/kernel/syscall.c']"),
 ("len(commands)==5,'exact five selected successor commands'","len(commands)==4,'exact four selected successor commands'"),
 ('all four changed compiler source paths','all three changed compiler source paths'),
 ("==7 and sum(r['replace'] for r in profile['inputs']['objects'])==4,'seven original retained and four new objects'","==8 and sum(r['replace'] for r in profile['inputs']['objects'])==3,'eight accepted retained and three new objects'"),
 ("set(outputs[:4]),'exact four selected replacement object paths'","set(outputs[:3]),'exact three selected replacement object paths'"),
 ("elif i<4:require(argv[0]","elif i<3:require(argv[0]"),
 ("name='current110-build-only-'","name='current111-build-only-'"),
]: runner=once(runner,a,b)
worker=(A/'build_only_worker.py').read_text()
worker=once(worker,"len(plan['commands'])==5,'exact five selected build commands'","len(plan['commands'])==4,'exact four selected build commands'")
worker=once(worker,'ACTUAL_BUILD_ONLY_FIVE_COMMAND_PRODUCER','ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER')
tools=[]
for name,text in [('run_build_only.py',runner),('build_only_worker.py',worker),('hold_and_run_build_only.py',(A/'hold_and_run_build_only.py').read_text()),('publish_approved_ready.py',(A/'publish_approved_ready.py').read_text())]:
    ast.parse(text,filename=name)
    dest=write(name,text.encode());before=(A/name).read_text()
    diff=''.join(difflib.unified_diff(before.splitlines(keepends=True),text.splitlines(keepends=True),fromfile='CURRENT110/'+name,tofile='CURRENT111/'+name))
    delta=write('tool-diffs/'+name+'.diff',diff.encode())
    tools.append(dict(name=name,predecessor=ref(A/name),successor=ref(dest),diff=ref(delta)))
export=copy.deepcopy(read(A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'))
export.update(status='CURRENT111_EXPORT_TEMPLATE_NOT_ACTUAL_AUTHORITY',author=None,decision=None,request_sha256=None)
export['qualified_readonly_files']=[r['source'] for r in profile['inputs']['configuration']]+[r['source'] for r in profile['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in postimages]+[r['snapshot'] for r in rows]
save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
save('DERIVATION.json',dict(scope=SCOPE,runtime_authority=None,predecessor_preparation=str(P),predecessor_admission=str(A),accepted_CURRENT110=ref(ACCEPTANCE),Root_adoptions=[ref(a) for a in ADOPTIONS],changed_Rust_sources=[r for r in rows if r['kind']!='unchanged CURRENT110'],changed_postimages=[dict(relative=r['relative'],predecessor=o['postimage'],successor=r['postimage']) for r,o in zip(postimages,old['inputs']['postimages']) if r['postimage']['sha256']!=o['postimage']['sha256']],unchanged_arch_source_and_command=old['exact_commands'][3],new_Rust_cfg='f03_perf_counter_control_bridges_selected_candidate',new_C_define='MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES',original_gates='Original CMake x86/native/ENABLE_PERF guards preserved; Rust cfg all(enable_perf,selector); process uses existing global-storage selector',exact_selectors_derived_from=ref(ROOT/'kernel/CMakeLists.txt'),retained_arch_object=next(r for r in profile['inputs']['objects'] if r['build_relative']==arch),tools=tools))
save('ROOT-NEXT-STEPS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,owner='/root',source_profile=ref(D/'PROFILE.SOURCE-ONLY.json'),exact_commands=ref(D/'EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json'),actual_nonce=None,actual_request=None,actual_resource_authority=None,actual_root_grant=None,actual_output_root=None,actual_holder=None,actual_independent_execution_review=None,required_next=[
 'Independently review exact closed112Rust map/adopted postimages, four literal command derivation and finite tool diffs; no completed build/sdk/HOST replay.',
 'Root binds actual current account/source/ownership/native custody/ledger30-or-newer and fresh nonce/request/output/export/publication. Old CURRENT110 authorities and consumed nonces confer no CURRENT111 authority.',
 'Use existing reviewed one-heavy holder/resource protocol after current read-only ownership and original-contract admission; CPU2-5/12GiB/no swap/512pids/networknone; permanent27:4/scratch21; HOST16GiB/scratch12GiB and any greater original packet floors; aggregate7jobs/23259332608B. No outer control modification.',
 'Root independently reviews and grants exact source-bound execution before publication/holder GO. Existing capture/materialization helpers must be rebound by Root; do not replay CURRENT110 actual materialization or finalizer.',
 'Root executes four commands once: full Rust, processC, kernel syscallC, raw11input link. Preserve first failure/prefix, actual resource usage and positive holder/container joins.',
 'Bind new actual three-object/ELF/11input/default qualifiers; all accepted CURRENT110 predicates remain exact-source obligations. Verify expected66+25=91C/48Rust/67process and new runqueue208 by real symbols/relocations/consumer bytes; expected counts are not acceptance.',
 'Independent final current-consumer review rereads inherited timer/idle/13line/logger/folded argument providers plus new PMU callback ABI and runqueue208. Preserve original scripted OPEN/FAIL and all originals.',
 'Only Root may integrate accepted actual results. Native/whole-file/M14/M15 remain OPEN without their separate matching proof.'
],limitations=['Source preparation only: zero compiler, SDK, Docker, guest, native, sudo, cleanup, execution release or READY publication operations.','No actual current admission/nonce/resource/physical clearance or source publication is fabricated.','Accepted CURRENT110 and HOST19 are not replayed; fresh CURRENT111 consumers are unproven.','No canonical files or outer account/guardian/ledger edited. Same credit run7f4af94a83b14cc08f97401f5891d965/57774.852125; cumulative spent>=22812.3311 and real holds remain effective.']))
save('SOURCE-READY.json',dict(scope=SCOPE,status='SOURCE_READY_MINIMAL_CURRENT111_FOUR_COMMAND_PROPOSAL_NOT_RELEASED',runtime_authority=None,profile=ref(D/'PROFILE.SOURCE-ONLY.json'),closed_Rust_source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),derivation=ref(D/'DERIVATION.json'),next_steps=ref(D/'ROOT-NEXT-STEPS.NOT-AUTHORITY.json'),tools=tools,commands=4,new_objects=3,retained_objects=8,closed_Rust_sources=112,Root_adopted_files_checked=5,source_only=True,actual_compilers=0,actual_native_apps=0))
print(json.dumps(dict(status='SOURCE_READY_NOT_RELEASED',Rust_files=112,commands=4,new_objects=3,retained_objects=8,canonical_mutations=0)))
