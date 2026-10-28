"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded source/profile correction review; no compiler/reader main/guard/query.
"""
from pathlib import Path
import ast,datetime,hashlib,json
D=Path(__file__).resolve().parent;Q=D.parent;P=Q.parent;E=P.parent;OLD=P/'callback-target-reader-source-clarification-1'
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
ready=read(Q/'SOURCE-READY.json');profile=read(Q/'PROFILE.NOT-GRANTED.json');old=read(OLD/'PROFILE.NOT-GRANTED.json');recipe=read(Q/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json');orcp=read(OLD/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')
assert ref(Q/'SOURCE-READY.json')['sha256']=='2e4b43e1f8dc6015fc2c4f66449af78c8372e71ef88f4cf1314b1330d68a0873'
assert ref(Q/'PROFILE.NOT-GRANTED.json')==ready['profile'] and ref(Q/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')==ready['commands']
assert ready['composition']==read(OLD/'SOURCE-READY.json')['composition'] and ready['open_predicates']==read(OLD/'SOURCE-READY.json')['open_predicates']
prior=OLD/'independent-source-profile-review-1/INDEPENDENT-SOURCE-PROFILE-REVIEW.json';assert ref(prior)['sha256']=='42da9e57262f8c768eaf9abf6dce31f6ceb1f8d1af6f0e8e5f8847eadfd5bea9'
manifest=OLD/'independent-source-profile-review-1/ACTUAL114-RETAINED-REGISTRY-COUNTEREXAMPLE.json';assert ref(manifest)==ready['retained_registry_counterexample']
assert profile['commands'][:6] and len(profile['commands'])==7
argv_delta=[]
for i,(a,b) in enumerate(zip(old['commands'],profile['commands'])):
 if i<6:assert a['argv']==b['argv']
 else:
  assert a['argv'][:2]==b['argv'][:2] and a['argv'][3:]==b['argv'][3:] and a['argv'][2]==str(OLD/'qualify_changed_objects.py') and b['argv'][2]==str(Q/'qualify_changed_objects.py')
  argv_delta.append(dict(command=i,changed_argument_index=2,old=a['argv'][2],new=b['argv'][2]))
 assert b['argv']==recipe['commands'][i]['argv'] and b['cwd']==str(P) and b['leaf']==profile['leaves'][0]['name']
assert all(profile[k]==old[k] for k in ['scope','goal','fixed_deadline_UTC','fixed_cutoffs','resources','host_growth_reserve_bytes','capture_root','production_acceptance','scope_limit'])
assert not Path(profile['capture_root']).exists() and not Path(profile['leaves'][0]['output']).exists()
oldpins={r['path']:r for r in old['inputs']};pins={r['path']:r for r in profile['inputs']};shared=set(oldpins)&set(pins)
assert all(oldpins[k]==pins[k] for k in shared)
assert str(Q/'qualify_changed_objects.py') in pins and '/usr/bin/cmake' in pins
assert ref('/usr/bin/cmake')==pins['/usr/bin/cmake'] and ref(Q/'qualify_changed_objects.py')==pins[str(Q/'qualify_changed_objects.py')]
assert pins[str(manifest)]==ref(manifest)
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';assert ref(runner)['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
t=ast.parse(runner.read_text());nodes=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in {'need','validate_profile'}]
ns=dict(Path=Path,hashlib=hashlib,json=json,THREAD='01a17e6f-112f-7660-8771-85d15e07a26c',CUTOFFS=[1793165769.0,947874.5689514667,963213.6960030915]);exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained ordinary validator only','exec'),ns);ns['validate_profile'](profile)
assert profile['internal_and_capture_bound_bytes']['total']==3154116608 and profile['host_growth_reserve_bytes']==4294967296

# Compare existing actual-object ABI/callback/folded-consumer logic exactly by AST;
# the bounded changes only separate the cohort from exhaustive whole-container data.
oldtree=ast.parse((OLD/'qualify_changed_objects.py').read_text());newtree=ast.parse((Q/'qualify_changed_objects.py').read_text())
functions={n.name:n for n in newtree.body if isinstance(n,ast.FunctionDef)}
for n in oldtree.body:
 if isinstance(n,ast.FunctionDef) and n.name!='main':assert ast.dump(n,include_attributes=False)==ast.dump(functions[n.name],include_attributes=False),n.name
assert {n.name for n in newtree.body if isinstance(n,ast.FunctionDef)}-{n.name for n in oldtree.body if isinstance(n,ast.FunctionDef)}=={'process_metadata','verbose_symbols','raw_verbose','preserve_unrelated','whole_container'}
source=(Q/'qualify_changed_objects.py').read_text();assert 'assert off%32==0' in source and "assert actual==expected" in source
assert "assert set(rel)==set(nrel) and normalized_raw(raw,rel)==normalized_raw(nraw,nrel)" in source
assert "assert {s['name']:s['size'] for s in actual}==expected" in source
assert "assert sum(z['size'] for z in elf.sections if z['name']=='__verbose')==6560" in source
assert "raise SystemExit(2)" in source and "nondefault_full_object_link_native_acceptance=False" in source
report=dict(scope=__doc__.splitlines()[0],decision='PASS_SOURCE_DEFAULT_LIMITED_LOCAL14_CONFIG3_FINAL14_HOST_QUALIFICATION_PREPARATION',reviewer='/root/current110_execution_review',independent=True,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ready=ref(Q/'SOURCE-READY.json'),profile=ref(Q/'PROFILE.NOT-GRANTED.json'),recipe=ref(Q/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json'),reader=ref(Q/'qualify_changed_objects.py'),prior_blocked_review=ref(prior),retained_actual114_counterexample=ref(manifest),unchanged_composition=ready['composition'],reused_positive_source_findings=read(prior)['unaffected_positive_findings'],argv_delta=argv_delta,producer_CPP_link_argv_unchanged=6,ordinary_command_rows=7,ordinary_metadata_validator='PASS existing6e98 validate_profile AST-extracted only; no import/main/admission',declared_input_counts=dict(before=len(oldpins),after=len(pins),same_refs=len(shared),added=len(set(pins)-set(oldpins)),removed=len(set(oldpins)-set(pins))),added_input_refs=[pins[k] for k in sorted(set(pins)-set(oldpins))],removed_input_refs=[oldpins[k] for k in sorted(set(oldpins)-set(pins))],
corrected_findings=[
'process_metadata supplies the unchanged original per-record ELF gate an exact46-name process view; original symbol tables and raw relocations remain intact. This view is accompanied by exhaustive separate whole-container and unrelated-record checks; extra/missing names cannot be accepted by filtering alone.',
'Whole selected Rust, selected partial joint and optionOFF partial joint each require exact148 names/sizes,205slots6560B and complete section total. Exact46-process cohort remains78slots2496B. Every102 unrelated retained record retains unique name/type/bind/size, alignment and GNU_RETAIN, packed flags/line/null/padding bytes, relocation positions and R64 type.',
'All unrelated file/function/format string literals compare to authenticated retained actual114. Only FILE slot changes may map original /src/kernel/process.c to exact candidate C env operand or an existing /src/kernel/rust/<known-source> to exact HOST Rust subtree operand. FUNC/FMT changes, unknown file contexts and numeric/flag suppression fail. This is HOST source-path context adaptation, not replacement of production/native registry metadata.',
'Original config384B/final256B actual ABI/scalar/padding/callback identity/local-address/readonly tests are AST-identical. Actual new Rust/C consumer readback, missing-folded-reference OPEN/exit2 and no-replay obligation remain unchanged. No actual object proof is claimed by this source receipt.',
'Existing6e98 profile schema now passes: fresh task prefix, absolute cwd, leaf and compactargv JSON+LF SHA. Six producer/CPP/link argv are identical; seventh changes only frozen incorrect-reader path to exact corrected reader. /usr/bin/cmake exact executable pin is added. Original CPU6/job1/AS2GiB/CPU60/FSIZE64MiB/CORE0/90s, aggregate7jobs/21.6619GiB, strict23357213694B memory floor, HOST16GiB+reserve and scratch12GiB remain unchanged.',
'All8 separate CPP -o files are now counted:3,154,116,608B conservative growth fits original4GiB reserve with1,140,850,688B headroom. No limit or free floor is reduced.',
'Four source files and108 selected Rust subtree source bodies are unchanged from42da reviewed candidate; existing119-entry map/context and original accepted GLOBAL32 prefix remain reused. No compiler/CPP/guest/query/guard or full shared hash loop was executed.'],
retained_open=['Actual seven command compilation/LLD21/CPP/reader results require fresh Root ordinary CPU6 grant and current account/resources.','Missing named consumer relocations remain OPEN for exact actual folded instruction/dataflow proof without compiler-prefix replay.','Selected defaultON rejects RUSAGE_DEBUG/TIMER_CPU_ID/ARCH_MEMCLEAR unless optionOFF; direct Fugaku selection rejects and CMake excludes it. Eight CPP controls do not establish all-profile object/link/native compatibility.','Production default adoption/link/native, supported whole-file retirement and M14/M15 completion remain OPEN.'],blocking_findings=[],runtime_authority=None,canonical_mutations=0,actual_compilers=0,actual_CPP=0,actual_qualifier_main=0,guard_or_resource_queries=0,workloads=0,passed_GLOBAL32_prefix_replays=0)
out=D/'INDEPENDENT-SOURCE-PROFILE-REVIEW.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(out),changed_runtime_source_files=0,producer_argv_unchanged=6,qualifier_path_changes=1,blocking_findings=0)))
