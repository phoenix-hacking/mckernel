"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source/ordinary-profile review; no compiler, guard, resource query or workload.
"""
from pathlib import Path
import ast,datetime,hashlib,json,struct
D=Path(__file__).resolve().parent;Q=D.parent;P=Q.parent;E=P.parent
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
ready=read(Q/'SOURCE-READY.json');profile=read(Q/'PROFILE.NOT-GRANTED.json');composition=read(P/'COMPOSITION-AND-LIMITS.json');recipe=read(Q/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')
assert ref(Q/'SOURCE-READY.json')['sha256']=='347bbd3ac6ef51d0e31fb6ef5776d1a36aca0f9274fd770758de7730c2e5e2dc'
assert ref(Q/'PROFILE.NOT-GRANTED.json')==ready['profile'] and ref(Q/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')==ready['commands']
assert ref(P/'COMPOSITION-AND-LIMITS.json')==ready['composition']
oldprofile=read(composition['actual114_source_profile']['path']);oldby={r['relative']:r['postimage'] for r in oldprofile['cohort_source_bindings']}
source=[]
for row in composition['proposed_files']:
 assert ref(row['preimage']['path'])==row['preimage'] and ref(row['candidate']['path'])==row['candidate']
 assert row['preimage']['sha256']==oldby[row['relative']]['sha256']
 source.append(row)
assert len(source)==4 and len(profile['commands'])==len(recipe['commands'])==7
pins={r['path']:r for r in profile['inputs']};assert len(pins)==len(profile['inputs'])==582
for a,b in zip(profile['commands'],recipe['commands']):
 assert a['argv']==b['argv']
 assert Path(a['argv'][0]).is_absolute()
 if a['argv'][0] not in pins:assert a['argv'][0]=='/usr/bin/cmake'
 assert a['purpose'].startswith('Functional') and 'no security testing' in a['purpose']
assert profile['resources']==dict(cpu=6,jobs=1,AS_bytes=2**31,CPU_seconds_each=60,FSIZE_bytes=64*2**20,CORE_bytes=0,wall_seconds_each=90,aggregate_jobs=7,aggregate_GiB='21.6619')
assert profile['fixed_cutoffs']==[1793165769.0,947874.5689514667,963213.6960030915]
assert profile['invocation_requirement']=='ABSOLUTE profile and grant paths'
assert not Path(profile['capture_root']).exists() and all(not Path(x['output']).exists() for x in profile['leaves'])
assert profile['commands'][6]['argv'][2]==str(Q/'qualify_changed_objects.py')
for suffix,sha in [('ordinary-host-new12h-runner-source-1/run_new12h_host.py','6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'),('ordinary-host-new12h-runner-source-1/admission_new12h.py','7df167b39842976391b6461f831c1a1349e1f3880892c37268579378e8f15a76'),('operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py','1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0')]:
 p=E/suffix;assert pins[str(p)]['sha256']==sha and ref(p)==pins[str(p)]
rs=[r for r in profile['inputs'] if r['path'].endswith('.rs') and '/rust-subtree/' in r['path']];assert len(rs)==108
for r in rs:
 relative='kernel/rust/'+r['path'].split('/rust-subtree/',1)[1]
 wanted=next((s['candidate'] for s in source if s['relative']==relative),oldby.get(relative));assert wanted and r['sha256']==wanted['sha256'],relative
assert all(not r['path'].startswith(profile['leaves'][0]['output']+'/') and not r['path'].startswith(profile['capture_root']+'/') for r in profile['inputs'])

# Reuse the accepted ELF reader only, to establish the exact frozen whole-Rust
# registry input that contradicts the standalone46-record checker assumptions.
f=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
ns=dict(Path=Path,struct=struct);node=next(n for n in ast.parse(f.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='_ReuseElf');exec(compile(ast.Module(body=[node],type_ignores=[]),'retained ELF class only','exec'),ns)
Elf=ns['_ReuseElf'];retained=recipe['retained_actual114_Rust'];assert ref(retained['path'])==retained
elf=Elf(Path(retained['path']));records=[s for s in elf.symbols if s['shndx'] and s['type']==1 and elf.sections[s['shndx']]['name']=='__verbose']
assert len(records)==134 and sum(s['size'] for s in records)==6112
map46=read(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f02-verbose46-source-1/EXACT46-SLOT78-MAP.json'))
globals32={r['name'] for r in map46 if not r['local']};locals14={r['name'] for r in map46 if r['local']}
assert len(globals32)==32 and len(locals14)==14
assert globals32<={s['name'] for s in records} and not locals14&{s['name'] for s in records}
others=[s for s in records if s['name'] not in globals32];assert len(others)==102 and sum(s['size'] for s in others)==4064
names=read(P/'EXACT14-TYPES-AND-CONSUMERS.json')['objects'];configs=read(P/'EXACT-LOCAL14-CONFIG3-MAP.json')['configs']
assert len(names)==14 and sum(r['bytes'] for r in names)==256 and len(configs)==3 and sum(r['bytes'] for r in configs)==384
oldc=Elf(Path(recipe['retained_actual114_process']['path']));oldobjects={s['name'] for s in oldc.symbols if s['type']==1 and s['shndx'] and oldc.sections[s['shndx']]['flags']&2}
assert oldobjects==locals14|{r['name'] for r in configs}|{r['name'] for r in names} and len(oldobjects)==31
registry_proof=dict(retained_actual114_Rust=retained,records=records,unrelated_retained_records=others,actual_existing_objects=134,actual_existing_slots=191,actual_existing_bytes=6112,proposed_added_LOCAL_objects=14,proposed_added_LOCAL_slots=14,proposed_added_bytes=448,expected_whole_Rust_and_selected_joint_objects=148,expected_whole_Rust_and_selected_joint_slots=205,expected_whole_Rust_and_selected_joint_bytes=6560,expected_exact_process_cohort_objects=46,expected_process_cohort_slots=78,expected_process_cohort_bytes=2496)
with (D/'ACTUAL114-RETAINED-REGISTRY-COUNTEREXAMPLE.json').open('x') as o:json.dump(registry_proof,o,indent=2);o.write('\n')
outer=7*2*64*2**20;cpp_logs=8*2*64*2**20;cpp_outputs=8*64*2**20;positive=5*64*2**20;metadata=128*2**20;temp=128*2**20;growth=outer+cpp_logs+cpp_outputs+positive+metadata+temp
assert growth==3154116608 and growth<profile['host_growth_reserve_bytes']==2**32
report=dict(scope=__doc__.splitlines()[0],decision='BLOCKED_SOURCE_REGISTRY_READER_AND_ORDINARY_PROFILE_SCHEMA',independent=True,reviewer='/root/current110_execution_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ready=ref(Q/'SOURCE-READY.json'),profile=ref(Q/'PROFILE.NOT-GRANTED.json'),recipe=ref(Q/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json'),composition=ref(P/'COMPOSITION-AND-LIMITS.json'),source_files=source,actual114_acceptance=ref(E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1/independent-artifact-review-1/INDEPENDENT-ACCEPTANCE.json'),counterexample=ref(D/'ACTUAL114-RETAINED-REGISTRY-COUNTEREXAMPLE.json'),
blocking_findings=[dict(id='FULL_RUST_READER_ASSUMES_STANDALONE46_REGISTRY',affected_command=6,reader=ref(Q/'qualify_changed_objects.py'),existing_reader=ref(E/'m14-f02-verbose32-host-preparation-source-1/qualify_metadata.py'),contract='Compile genuine wholecurrentRust and qualify exact LOCAL14+config3+final14 while preserving unrelated accepted descriptors.',failure='metadata(rust,allrows) and metadata(joint,allrows) call existing metadata(), which requires total __verbose symbol count ==46. Genuine retained114 wholeRust already contains134 objects/191slots6112B; candidate adds14 objects/448B ->148 objects/205slots6560B. The joint2496B total assertion is also false. This is deterministic before any proposed compiler execution.',minimal_correction='Qualify exact46 process names/78slots2496B as a bounded subset of whole Rust/joint. Preserve exact102 other retained record identities/127slots4064B and require total148objects/205slots6560B for this exact tuple, or use truthful whole-registry preservation with cohort subset checks. Do not drop unrelated records or rerun GLOBAL32 passed-prefix tests. Rebind only corrected reader/profile/source receipts; no port rewrite or broad parser pipeline.')],
unaffected_positive_findings=[
'Four candidate source files match declared bytes and actual114 preimages. Existing bodies remain;14 internal descriptors,3 immutable existing typed configs384B and14 readonly cells256B exactly cover actual114 process31 C objects. This is a proposed data-owner change, not a new computation port.',
'CMake jointly selects C suppression/Rust ownership under x86 Rust enabled, verboseDATA ON, local optionON, Linux6.12 ABI, UBSANOFF, debugprintOFF and FugakuOFF. Defaults preserve flags0. OptionOFF retains original C definitions and static internal linkage.',
'Selected C explicitly rejects RUSAGE_DEBUG/TIMER_CPU_ID/ARCH_MEMCLEAR/Fugaku; bounded8 CPP recipes test selected rejection and optionOFF preprocessing. No all-profile object/link/native claim is made. Fugaku CMake exclusion is real, not supported-variant qualification.',
'Rust reuses existing repr(C) configs, ArchMemclear callback alias and actual SchedExitDebug pointee. ReadonlyPointerCell reprtransparent Sync shares immutable raw cell bits only; no pointee Sync, dereference or new lifetime ownership.14 descriptors retain LLVM internal linkage, used/retain and mutable flags storage.',
'Genuine C fixture includes complete candidate TU and asserts all3 companion config offsets/scalars/sizes/alignments plus168B init-stack ABI. Object reader compares actual original config scalar/padding bytes, filename context,14 internal descriptor addresses and callback symbol identities, including defined C callbacks. Missing folded named references deliberately remain OPEN and exit2 for independent actual instruction/dataflow proof.',
'WholeRust command binds108 project Rust sources through declared hashes:106 unchanged accepted114 sources plus2 declared changed files;11 additional .rs input references are also pinned. Profile has582 declared pins; no broad hash replay was performed.',
'Exact7 absolute executable argv/purpose bindings match recipe; ordinary wrapper cwd/leaf/argvSHA fields are missing and BLOCKED as separately recorded; selectedC/optionOFF C, selected/fallback partial LLD21 links,8 fixed CPP and readback stay on CPU6/job1/AS2GiB/CPU60/FSIZE64MiB/CORE0/90s each. Fresh output/capture absent. Runner6e98/admission7df/v2guard1f152 unchanged;23357213694B memory floor,HOST16GiB+growth,scratch12GiB,7 aggregate jobs/21.6619GiB and original fixedclocks preserved.',
'No actual compiler/CPP/qualification reader main/guard/resource query/workload/admission/canonical/Git action was performed.'],
resource_accounting_disclosure=dict(declared_total_bytes=profile['internal_and_capture_bound_bytes']['total'],omitted_eight_CPP_output_file_bound_bytes=cpp_outputs,conservative_total_bytes=growth,full_reserve_bytes=profile['host_growth_reserve_bytes'],remaining_headroom_bytes=profile['host_growth_reserve_bytes']-growth,blocking=False,explanation='Declared internal total counts8 CPP stdout/stderr pairs but omits8 separately named -o preprocessed files. Existing4GiB reserve still covers all such64MiB file bounds with1.0625GiB headroom; amend bookkeeping when sealing successor without weakening limits.'),
missing_executable_pin=dict(path='/usr/bin/cmake',affected_command=0,required_correction='Add exact CMake executable path/bytes/SHA pin; other three outer executable paths are already declared.'),ordinary_schema_blocker=dict(task_id=profile['task_id'],required_task_id_prefix='NEW12H-ORDINARY-HOST-',missing_command_fields={str(i):[k for k in ['cwd','leaf','argv_compact_json_LF_sha256'] if k not in r] for i,r in enumerate(profile['commands'])},required_correction='Preserve seven exact argv; wrap with existing6e98 absolute cwd, leaf identifier, compactargv JSON+LF SHA and valid fresh task identifier.'),source_or_profile_grant=False,actual_compilers=0,actual_CPP=0,actual_workloads=0,guard_or_resource_queries=0,canonical_mutations=0,passed_GLOBAL32_prefix_replays=0,native_acceptance=False,whole_file_retirement=False)
out=D/'INDEPENDENT-SOURCE-PROFILE-REVIEW.json'
with out.open('x') as o:json.dump(report,o,indent=2);o.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(out),changed_source_files=4,blocking_findings=3,next_blocker='Scope exact46-name process subset within genuine148-object wholeRust registry; retain102 unrelated records.')))
