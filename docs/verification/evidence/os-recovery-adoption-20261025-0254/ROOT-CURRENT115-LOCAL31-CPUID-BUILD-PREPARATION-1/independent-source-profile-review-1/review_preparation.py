"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
CURRENT115 source/mechanical preparation review; never calls guard/observer/main.
"""
from pathlib import Path
import ast,copy,datetime,hashlib,json,os
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent;C=P/'materializer-external-input-authentication-correction-source-1';S=E/'next115-f02-local31-f06-cpuid-source-integration-preparation-1';A=E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
r=read(P/'SOURCE-READY.json');cr=read(C/'SOURCE-READY.json');m=read(C/'PREPARATION-MANIFEST.json');p=read(P/'PROFILE.TEMPLATE.SOURCE-ONLY.json');b=read(P/'ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');op=read(A/'PROFILE.SOURCE-ONLY.json');accepted=read(A/'independent-artifact-review-1/INDEPENDENT-ACCEPTANCE.json')
assert ref(P/'SOURCE-READY.json')['sha256']=='d78dc4f6a33323e643ee0fd2802382d2b3777d21b4c3b928be41750616c8b536'
assert ref(C/'SOURCE-READY.json')['sha256']=='fb7b89d7317707c2d21f77066f8d41a67b3cbf4f208733c6762ebc81b11e2ddf'
assert ref(P/'PROFILE.TEMPLATE.SOURCE-ONLY.json')==r['profile']==cr['profile'] and ref(C/'PREPARATION-MANIFEST.json')==cr['manifest']
for row in m['files']+m['external_inputs']:assert ref(row['path'])==row
assert len(m['external_inputs'])==7
source_review=S/'independent-source-profile-review-1/REVIEW.json';assert ref(source_review)['sha256']=='cbfbc39e3afa36d863d29e219f2c4a760e6dc8e7b6edeaba13dc77989804394b' and read(source_review)['decision']=='PASS_SOURCE'
recipe=read(S/'SELECTIVE-SOURCE-RECIPE.json');commands=read(S/'NEXT115-COMMAND-RECIPE.NOT-GRANTED.json');assert p['exact_commands']==commands['commands'] and len(p['exact_commands'])==4
adoption=read(r['actual_source_adoption']['path']);assert ref(r['actual_source_adoption']['path'])==r['actual_source_adoption'] and adoption['author']=='/root' and len(adoption['source_changes'])==len(recipe['files'])==9
wanted={x['relative']:x['candidate']['sha256'] for x in recipe['files']}
for row in adoption['source_changes']:assert ref(row['after']['path'])==row['after'] and row['after']['sha256']==wanted.pop(row['relative'])
assert not wanted and all('shmget' not in x['relative'] for x in recipe['files'])
retained=[];oldobjects={x['link_token']:x for x in op['inputs']['objects']}
for row in p['inputs']['objects']:
 if row['replace']:continue
 old=oldobjects[row['link_token']]
 expected=accepted['tuple']['kernel_C'] if row['link_token']=='CMakeFiles/mckernel.img.dir/syscall.c.o' else old['source']
 assert row['source']==expected and ref(row['source']['path'])==row['source'] and row['source']['bytes']>0
 retained.append(row)
assert len(retained)==8 and len(p['inputs']['objects'])==11 and sum(x['replace'] for x in p['inputs']['objects'])==3
assert {x['link_token'] for x in p['inputs']['objects'] if x['replace']}=={'rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'}
for name in ['build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:assert (P/name).read_bytes()==(A/name).read_bytes()
for key in ['CPU','memory_bytes','pids','maximum_wall_seconds','deadline_epoch','fixed_three_clock_cutoffs','aggregate_memory_budget_bytes','docker_client_prefix']:assert p[key]==op[key]
oldrunner=(A/'run_build_only.py').read_text();newrunner=(P/'run_build_only.py').read_text();expected=oldrunner.replace("outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/process.c.o','mckernel.img']","outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']").replace("sources=['/src/kernel/rust/lib.rs','/src/kernel/syscall.c','/src/kernel/process.c']","sources=['/src/kernel/rust/lib.rs','/src/kernel/process.c','/src/arch/x86_64/kernel/syscall.c']").replace("origin_target.touch(mode=0o400,exist_ok=False)","origin_target.touch(mode=0o400,exist_ok=False)\n    metadata_target=origin_target.parent/'f06_clone_cpuid_metadata.rs'\n    require(not os.path.lexists(metadata_target),'fresh exact cpuid metadata bind target')\n    metadata_target.touch(mode=0o400,exist_ok=False)").replace("name='current114-build-only-'","name='current115-build-only-'")
assert expected==newrunner
oldmat=(P/'materialize_admission.py').read_text();newmat=(C/'materialize_admission.py').read_text()
expected=oldmat.replace('D=Path(__file__).resolve().parent;E=D.parent','C=Path(__file__).resolve().parent;D=C.parent;E=D.parent').replace("assert b['preparation_manifest']==ref(D/'PREPARATION-MANIFEST.json')\n for row in read(auth(b['preparation_manifest']))['files']:auth(row)","assert b['preparation_manifest']==ref(C/'PREPARATION-MANIFEST.json')\n manifest=read(auth(b['preparation_manifest']))\n for row in manifest['files']:auth(row)\n for row in manifest['external_inputs']:auth(row)")
assert expected==newmat

# Existing static validator only: request digest is a local test value, never an
# actual authority/artifact/hash publication. No account or resource method called.
tree=ast.parse(newrunner);names={'require','reference','auth','read','strict_parent','source_directory_postimages','commands_for_plan','mounts'};ns=dict(Path=Path,hashlib=hashlib,json=json,os=os,D=P)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'existing exact source-map/command/mount functions only','exec'),ns)
rows=ns['source_directory_postimages'](p);assert len(rows)==120
v=copy.deepcopy(p);v['request_sha256']='0'*64;v['cohort_source_bindings']=[dict(relative=x['relative'],postimage=x['postimage']) for x in v['inputs']['postimages']]+rows
assert ns['commands_for_plan'](v)==p['exact_commands']
export=read(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json');mounts=ns['mounts'](v,export,E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1/OUTPUT');assert len({x['target'] for x in mounts})==len(mounts) and all(x['readonly'] for x in mounts)
# Fresh origin: actual joined generator, all five exact output references, no
# historical113 origin substitution. Validate the same source/argv conditions.
origin=read(b['actual_origin_producer']['path']);assert ref(b['actual_origin_producer']['path'])==b['actual_origin_producer']
assert origin['source_generation_only'] and not origin['compiler_executed'] and origin['returncode']==0 and origin['direct_child_joined'] and origin['streams_closed']
assert origin['argv']==read(P/'ROOT-ORIGIN-PRODUCER-PROPOSAL.NOT-GRANTED.json')['argv']
for key in ['actual_generated_header','actual_generated_metadata','actual_origin_binding','actual_Rust_environment','actual_CMake_origin']:assert ref(b[key]['path'])==b[key]
assert b['actual_generated_header'] in origin['outputs'] and b['actual_generated_metadata'] in origin['outputs']
ctx=read(b['actual_origin_binding']['path']);spec=read(S/'candidate/scripts/f06_origin_command_profile.json')
assert ctx['source_sha256']==recipe['files'][0]['candidate']['sha256'] and ctx['profile_sha256']==ref(S/'candidate/scripts/f06_origin_command_profile.json')['sha256']
assert ctx['command']=={k:p['exact_commands'][2][k] for k in ['stage','cwd','argv','new_output']} and ctx['origin_utf8']=='/src/arch/x86_64/kernel/syscall.c'
assert ctx['clone_cpuid_debug_slots']==spec['clone_cpuid_origin_reference']['retained_C_metadata']
metadata=Path(b['actual_generated_metadata']['path']).read_text();assert 'F06_CLONE_CPU_SAMPLE_LINE_FLAGS: u32 = 898;' in metadata and 'F06_CLONE_CPU_CHOICE_LINE_FLAGS: u32 = 908;' in metadata
assert 'MCKERNEL_F06_CLONE_CPUID_METADATA_RS=/work/output/build/kernel/rust/f06-origin/f06_clone_cpuid_metadata.rs' in p['exact_commands'][0]['argv']
for target in ['/work/output/build/kernel/rust/f06-origin/f06_rt_sigreturn_origin.h','/work/output/build/kernel/rust/f06-origin/f06_clone_cpuid_metadata.rs']:
 assert len([x for x in mounts if x['target']==target])==1
ledger=read(b['nonce_ledger']['path']);assert ref(b['nonce_ledger']['path'])==b['nonce_ledger']==r['actual_Root48'] and len(ledger['consumed_nonces'])==59 and b['nonce']==r['reserved_unused_nonce'] and b['nonce'] not in ledger['consumed_nonces']
assert b['current_boundary'] is b['mechanical_source_profile_review'] is None and all(b[k] is None for k in ['actual_source_publication','actual_resource_authority','actual_execution_review','actual_execution_grant'])
observer=P/'current-boundary-observer-source-1/observe_root48_current115.py';obs=observer.read_text();ast.parse(obs)
assert "len(ledger['consumed_nonces']) == len(set(ledger['consumed_nonces'])) == 59" in obs and r['actual_Root48']['sha256'] in obs and '563d0ce4db6695fb78adfaae2d2d91ca02afa6fa9c1621704d071b883718b89e' in obs
assert "boundary['nonce_ledger'] == ROOT48_LEDGER and boundary['native_custody_clearance'] == ROOT48_FREE" in obs and "assert boundary['observer'] == ref(Path(__file__))" in obs
assert "return finish_current235(value, ledger, census, guard)" in obs and "'latest235_actual30_clients_reaped':" not in obs # validated explicit update kwargs, not a fake literal report.
report=dict(scope=__doc__.splitlines()[0],decision='PASS_SOURCE_CURRENT115_FOUR_COMMAND_BUILD_PREPARATION_WITH_EXTERNAL_MANIFEST_AUTHENTICATION',independent=True,reviewer='/root/current110_execution_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_ready=ref(P/'SOURCE-READY.json'),corrected_materializer_ready=ref(C/'SOURCE-READY.json'),corrected_manifest=ref(C/'PREPARATION-MANIFEST.json'),profile=ref(P/'PROFILE.TEMPLATE.SOURCE-ONLY.json'),materializer=ref(C/'materialize_admission.py'),source_review=ref(source_review),actual_source_adoption=r['actual_source_adoption'],actual_new_origin=b['actual_origin_producer'],Root48=b['nonce_ledger'],reserved_unused_nonce=b['nonce'],F02_actual_HOST31_folded16=ref(E/'m14-f02-local14-final14-qualified-preparation-source-1/independent-actual-qualification-review-1/INDEPENDENT-ACTUAL-HOST-ACCEPTANCE.json'),retained8=retained,readonly_mounts=mounts,closed_Rust_files=120,exact_compiler_link_commands=4,fresh_objects=3,retained_objects=8,original_seven_zero_mount_target_reference_corrections=ref(P/'RETAINED-MOUNT-TARGET-REFERENCE-CORRECTION.json'),existing_pure_validator_PASS=True,observer_source_contract=ref(observer),
findings=['Exact current115 nine-path source adoption matches cbfbc source review/recipe; no F03/shmget addition. Prior F02 HOST31/16 folded obligations remain bound only at HOST scope; new production artifacts still require actual checks.',
'All four argv match approved115 recipe. Raw link has identical11 input tokens; three fresh objects are wholeRust/processC/archC and eight genuine accepted114 inputs remain readonly. Retained kernel syscall object is actual114359600B/61Cfunction artifact; seven other old OUTPUT mount placeholders are replaced by real accepted profile source refs, not zero-byte files or recompiled objects.',
'Worker/holder/publisher are byte-identical actual114 helpers. Runner differs only fixed source/output map, fresh generated CPUID metadata bind target and115 container name. Both header/metadata bind targets are precreated and uniquely mounted readonly; no header generation/configure/SDK replay occurs inside fourcommands.',
'Fresh genuine115 origin producer is actual joined0/source-only; header/metadata/context/env/CMake refs authenticate exact archCsource/argv and original line_flags898/908. Historical113 origin is not used for changed115 arch.120-file closed Rust directory map is checked by original validator without hashing unchanged source-file content again.',
'Original materializer omitted new external_inputs authentication. The preserved corrective successor adds exact seven external refs to existing auth loop before their reads; all other staging logic is byte-equivalent after parent/manifest path adaptation. Full manifest closure now binds recipe/review/adoption/origin/reservation metadata.',
'Corrected static materializer permits only Root one-shot metadata/readonly exports and holder-only bootstrap. It still requires Root actual current-boundary, nonce ledger, positive current-free and independent source/boundary/mechanical references before staging; actual resource/review/grant/publication are honestly NULL until their phases.',
'Current observer contract pins Root48/59consumed, accepted235free563d, all30client positive reaps/33actor absence/five exact latest queries, twelve ordinary-operation joins and inherited mutex/cgroup/CID/actor controls. Source only was read; no observe(), guard(), subprocess query or ownership observation was called. Actual observer source approval and fresh execution remain bound through Root current-boundary document.',
'Existing one-heavy CPU2-5/12GiB/no swap/512tasks/no network and aggregate23259332608B, fixedthreeclocks, original account/boot/v2guard, HOST16GiB/scratch14091616256B, physical-before-holder and120s freshness/publisher exact-approvedSHA controls remain unchanged. Legacy generated publisher reviewer label is retained; actual independent execution approval must be a separate truthful receipt.',
'Current115 top-level3new/8retained/fourargv/neworigin predicates are authoritative. Historical cohort-specific prose in inherited postbuild list stays at its original scope; it does not prohibit this explicitly reviewed fresh archC/neworigin or imply obsolete count acceptance.'],
Root_next_command=cr['Root_next_command'],Root_binding_required_manifest=ref(C/'PREPARATION-MANIFEST.json'),required_before_static_stage=['Fill Root exact current-boundary observer and independent boundary review; nonce ledger Root48/free563d must remain current or a source-bound successor is needed.','Use corrected materializer and corrected manifest9ab427; original d78 materializer is preserved historical and not the reviewed next command.'],required_before_compiler=['Actual Root-only materialization and exact source publication/fetched-blob evidence.','Fresh preholder physical observation, holder27:4 only grant, actual held resources and reservations within original floors/limits.','Separate actual independent execution PASS for exact pending input SHA within120s; Root then invokes unchanged publisher once and existing live holder consumes READY.'],required_after_build=['Wait all actual commands/normal joins, preserve first failure and untouched suffix; no automatic prefix replay.','Actual new production ELF/Rust ownership/ABI/31data/2Ddebug/current-consumer and all inherited gates; counts/native/whole-file remain unaccepted until matching proofs.'],blocking_findings=[],runtime_authority=None,materialization_actions=0,compiler_actions=0,CPP=0,observer_main_actions=0,guard_or_resource_queries=0,canonical_mutations=0)
out=D/'INDEPENDENT-SOURCE-PROFILE-REVIEW.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(out),commands=4,new_objects=3,retained=8,Rust_files=120,blocking_findings=0)))
