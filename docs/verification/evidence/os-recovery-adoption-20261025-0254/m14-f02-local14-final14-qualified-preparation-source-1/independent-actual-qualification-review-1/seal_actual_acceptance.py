"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent actual HOST qualification plus finite folded-consumer supplement.
"""
from pathlib import Path
import datetime,hashlib,json
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent;Q=P/'typed-timer-array-alignment-reader-correction-source-1';B=P/'relative-module-context-correction-source-1/HOST-output-proposed-1'
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
report_path=Q/'QUALIFIER-output-proposed-1/LOCAL14-FINAL14-HOST-QUALIFICATION.json';r=read(report_path);profile=read(Q/'PROFILE.NOT-GRANTED.json');grant=read(Q/'ROOT-ACTUAL-ONE-QUALIFIER-HOST-GRANT-1.json');results=read(Q/'future-capture-1/RESULTS.json');source_review=Q/'independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json'
assert ref(source_review)['sha256']=='7d598e57140a2108d82bbccd76dddcafaad8c08bd2dd224b38232b587f510f08'
assert grant['profile_sha256']==ref(Q/'PROFILE.NOT-GRANTED.json')['sha256'] and grant['authorized'] and grant['authorized_by']=='Root'
command=read(Q/'future-capture-1/step0/command.json');assert command==profile['commands'][0]
assert len(results['results'])==1;j=results['results'][0]['join'];assert j['returncode']==2 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']
assert (Q/'future-capture-1/step0/stderr').read_bytes()==b''
assert r['status']=='OPEN_CURRENT_FOLDED_CONSUMER_SUPPLEMENT_REQUIRED' and len(r['open_predicates'])==16
assert r['counts']==dict(internal_debug_objects=14,slots=14,bytes=448,config_objects=3,config_bytes=384,final_objects=14,final_bytes=256)
assert [(x['objects'],x['slots'],x['R64_file_function_relocations']) for x in r['registry']]==[(46,78,156),(0,0,0),(46,78,156),(14,14,28)]
assert all((x['objects'],x['slots'],x['bytes'])==(148,205,6560) for x in r['whole_registry']) and len(r['whole_registry'])==3
assert len(r['retained102_provenance'])==3 and all((x['objects'],x['slots'],x['bytes'])==(102,127,4064) for x in r['retained102_provenance'])
assert len(r['local14_configs'])==3 and sum(x['bytes'] for x in r['local14_configs'])==384 and all(x['readonly'] and x['exact_scalar_padding_bytes'] for x in r['local14_configs'])
assert len(r['final14'])==14 and sum(x['bytes'] for x in r['final14'])==256 and all(x['readonly'] and x['exact_nonpointer_bytes'] for x in r['final14'])
assert len(r['current_consumer_readback'])==17 and sum(x['positive_current_reference'] for x in r['current_consumer_readback'])==1
assert next(x['name'] for x in r['current_consumer_readback'] if x['positive_current_reference'])=='process_clone_config'
config=read(D/'THREE-CONFIG-FOLDED-ABI-ARGUMENTS.json');cells=read(D/'FINAL-CELL-FOLDED-CONSUMER-SUPPLEMENT.json')
assert len(config['proofs'])==3 and sum(len(x['field_arguments']) for x in config['proofs'])==54
closed={
'process_copy_entry_config':'Three-config ABI proof15 fields; extra visit_flags1 and nowait2 actual visitor-context/allocation lowering.',
'process_extend_region_entry_config':'Three-config ABI proof18 scalar/pointer fields forwarded to genuine complete body.',
'process_init_stack_entry_config':'Three-config ABI proof21 scalar/callback fields forwarded to genuine complete body;168B/align8 preserved.',
'process_schedule_exit_debug_input':'Eight-byte readonly NULL; explicit rusage frame+RET and schedule RCX=0 tailargument4 to genuine sched_schedule_exit_cleanup.',
'process_sched_timer_configuration':'Readonly [CInt;2]=[0,0],size8/align4; complete actual timer bridge frame+RET.',
'process_init_stack_free_line':'Actual3364 immediate in R8D argument5 to pagealloc_track_free_result.',
'process_init_stack_free_file':'Exact candidate C filename NUL string R64/MOVABS in RCX argument4 to pagealloc_track_free_result, no intervening branch/overwrite.',
'process_init_stack_alloc_line':'Actual3359 stack eighth argument to _ihk_mc_alloc_aligned_pages_node.',
'process_init_stack_alloc_file':'Exact candidate C filename NUL string R64/MOVABS pushed as seventh argument to _ihk_mc_alloc_aligned_pages_node.',
'process_page_fault_anon_alloc_file':'Exact candidate C filename NUL string pushed as seventh aligned-page allocator argument; existing3058 line retained.',
'process_page_fault_cow_alloc_line':'Actual3145 stack eighth argument to _ihk_mc_alloc_aligned_pages_node.',
'process_page_fault_cow_alloc_file':'Exact candidate C filename NUL string pushed as seventh aligned-page allocator argument.',
'process_remap_free_line':'Actual2469 immediate in R8D argument5 to pagealloc_track_free_result.',
'process_remap_free_file':'Exact candidate C filename NUL string in RCX argument4 to pagealloc_track_free_result.',
'process_add_range_arch_memclear_callback':'Readonly eight-byte None/NULL; actual complete zeroing loop equals old default NULL-path loop under finite register rename/branch relocation/noops, same genuine physical-view selector/base.',
'process_tracked_allocator_source_file':'Actual process_alloc_bridge FILE literal RDX argument3 to _kmalloc; all33 original compiled cell users also carry positive exact NUL literal R64/MOVABS operands.'}
assert set(closed)=={x['name'] for x in r['open_predicates']}
identities=read(P/'absolute-retained-reference-correction-source-1/RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json');by={x['reference']['path']:x['reference'] for x in identities['records']}
artifacts={}
for name in ['rust-selected.o','selected.o','optionOFF.o','selected-joint.o','optionOFF-joint.o']:
 current=ref(B/name);assert current==by[str(B/name)];artifacts[name]=current
assert config['Rust']==cells['Rust']==artifacts['rust-selected.o']
prefix_results=read(identities['original_results']['path']);assert ref(identities['original_results']['path'])==identities['original_results']
metrics=[]
for row in prefix_results['results'][:6]:
 v=row['join'];assert v['returncode']==0 and v['direct_child_joined'] and v['group_absent'] and v['closed_streams'] and not v['error'] and not v['retirement_error']
 metrics.append(dict(index=row['index'],returncode=0,wall_seconds=v.get('elapsed_seconds',v.get('wall_seconds')),positive_join=True,groups_absent=True,closed_streams=True))
assert prefix_results['results'][6]['join']['returncode']==1
for x in r['retained102_provenance']:
 assert len(x['records'])==102 and all(v['exact_packed_bytes_and_relocation_positions'] for v in x['records'])
proofs={p.name:ref(p) for p in [D/'THREE-CONFIG-FOLDED-ABI-ARGUMENTS.json',D/'FINAL-CELL-FOLDED-CONSUMER-SUPPLEMENT.json',D/'TRACKED33-FILENAME-LITERAL-EDGES.CORRECTED.json',D/'ACTUAL-FOLDED-CONSUMER-INPUTS.json']}
accept=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_HOST_LOCAL14_CONFIG3_FINAL14_STORAGE_ABI_AND_FOLDED_CONSUMERS',independent=True,reviewer='/root/current110_execution_review',recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_review=ref(source_review),profile=ref(Q/'PROFILE.NOT-GRANTED.json'),Root_grant=ref(Q/'ROOT-ACTUAL-ONE-QUALIFIER-HOST-GRANT-1.json'),Root_CPU6_observation=ref(Q/'ROOT-ACTUAL-CPU6-EXCLUSION-1.json'),actual_report=ref(report_path),actual_qualifier_results=ref(Q/'future-capture-1/RESULTS.json'),actual_qualifier_command=ref(Q/'future-capture-1/step0/command.json'),child_stderr=ref(Q/'future-capture-1/step0/stderr'),actual_qualifier_child_returncode=2,actual_qualifier_normal_join=True,parent_reported_wrapper_terminal=dict(session=47578,returncode=1,attribution='Root task message; mechanical wrapper rejects intentional child2 OPEN as a failed ordinary command. Never relabeled0.'),original_report_OPEN_preserved=True,retained_six_producer_results=identities['original_results'],six_passed_prefix=metrics,retained41_identity_manifest=ref(P/'absolute-retained-reference-correction-source-1/RETAINED-SIX-PREFIX-INPUT-IDENTITIES.json'),actual_artifacts=artifacts,folded_proofs=proofs,closed_original16_predicates=closed,remaining_folded_consumer_predicates=[],
actual_scope=dict(new_HOST_owned_data_objects=31,internal_Ddebug_objects=14,internal_Ddebug_bytes=448,companion_configs=3,companion_config_bytes=384,final_readonly_objects=14,final_readonly_bytes=256,process_registry_objects=46,process_slots=78,process_registry_bytes=2496,whole_registry_objects=148,whole_registry_slots=205,whole_registry_bytes=6560,unrelated_retained_objects=102,unrelated_retained_slots=127,unrelated_retained_bytes=4064,config_folded_ABI_fields=54,tracked_positive_literal_users=33),
findings=['Six exact wholeRust/genuineC/optionOFFC/selectedLLD21/fallbackLLD21/fixedCPP commands passed0 with complete normal joins, and their existing objects are byte-identical to retained manifest. None is replayed. The qualifier completes all storage/ABI/registry checks then truthfully emits OPEN and exits2 for16 absent named relocations; this independent supplement closes those16 with positive actual instructions and pointer/string provenance.',
'Fourteen new internal descriptors remain LOCAL symbols with original32B/align8 mutable flags and exact FILE/FUNC/LINE/FMTNULL/flags0/padding; three configs384B preserve original scalar/padding bytes and14 exact LOCAL pointer fields. Fourteen readonly objects256B preserve true existing types and callback aliases; timer array uses its genuine4-byte alignment; initstack retains168B/align8 and all nine callback identities.',
'Selected and fallback partial links retain exact process46/78slots2496B within exhaustive148/205slots6560B. Every102 unrelated record retains identity/binding/size/packed values/relocation positions and exact supported source-string provenance. Original GLOBAL32 positive scope is reused, not counted as a new port or replayed legacy qualification batch.',
'New selected Rust17 immutable globals remain readonly. C fallback17 storage classes are exact original HOST per-name .data.rel.ro[.local]/WA or .rodata/A; no generic writable or physical partial-link RELRO acceptance. Fallback partial joint deliberately reuses accepted114 Rust at original source context and verifies C fallback ownership/storage/link scope; it is not whole-profile native qualification.',
'Three fixed forwarders encode54 exact config-derived SysV arguments, including actual LOCAL descriptors/callbacks and filename cells. Copy extra flags1/nowait2 are positive actual visitor-context/allocator arguments. Timer/rusage are complete6B returns; schedule passes actual NULL in RCX to real cleanup. FILE/line cells appear in exact actual allocation/free register/stack arguments. Memclear selectedNone retains the entire original zeroing loop under exact finite register/branch normalization.',
'Private candidate HOST boundary acceptance only. Original failed compile, readonly-reader failure, alignment-reader failure, blocked source packets and final child2/mechanical wrapper1 remain preserved. All original optionOFF/unsupported-defaultON, native, production and whole-file distinctions remain explicit.'],
retained_open=['Root production source adoption, genuine default CMake/build/final link/ownership and native use are not supplied by this private HOST receipt.','Selected defaultON rejects RUSAGE_DEBUG/TIMER_CPU_ID/ARCH_MEMCLEAR unless optionOFF; Fugaku remains excluded. Eight CPP checks prove preprocessing/rejection only, not all-supported-profile object/link/native behavior.','Physical C partial-link readonly/RELRO, supported whole-file retirement and M14/M15 completion remain OPEN.','Current resource/CPU6/native custody release is separate; this receipt grants no operation authority.'],blocking_findings=[],runtime_authority=None,producer_CPP_link_replays=0,compiler_actions=0,native_actions=0,guard_or_resource_queries=0,canonical_mutations=0,default_production_acceptance=False,native_acceptance=False,whole_file_retirement=False)
out=D/'INDEPENDENT-ACTUAL-HOST-ACCEPTANCE.json'
with out.open('x') as f:json.dump(accept,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=accept['decision'],receipt=ref(out),HOST_data_objects=31,closed_folded_predicates=16,remaining_folded_predicates=0,producer_replays=0)))
