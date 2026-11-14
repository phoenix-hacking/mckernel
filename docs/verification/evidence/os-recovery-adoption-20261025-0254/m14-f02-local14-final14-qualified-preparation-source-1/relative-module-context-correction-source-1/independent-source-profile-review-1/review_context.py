"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source-context correction review; no compiler/CPP/guard/resource/workload.
"""
from pathlib import Path
import ast,datetime,hashlib,json,re
D=Path(__file__).resolve().parent;Q=D.parent;P=Q.parent;E=P.parent;OLD=P/'registry-scope-profile-schema-correction-source-1'
read=lambda p:json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
ready=read(Q/'SOURCE-READY.json');profile=read(Q/'PROFILE.NOT-GRANTED.json');old=read(OLD/'PROFILE.NOT-GRANTED.json');context=read(Q/'CLOSED-RUST-MODULE-CONTEXT.json');oldmap=read(P/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')
assert ref(Q/'SOURCE-READY.json')['sha256']=='bcb03665dade5fea197f5757201ff82845ba01943a288330aa8c7cc312b7ae49'
assert ref(Q/'PROFILE.NOT-GRANTED.json')==ready['profile'] and ref(Q/'CLOSED-RUST-MODULE-CONTEXT.json')==ready['closed_context']
prior=OLD/'independent-source-profile-review-1/INDEPENDENT-SOURCE-PROFILE-REVIEW.json';assert ref(prior)['sha256']=='a9f816f5f9627c652c99423eb5785551de54d0b8d212d967d23d4c49c06b2d65'
assert ready['composition']==read(OLD/'SOURCE-READY.json')['composition'] and ready['open_predicates']==read(OLD/'SOURCE-READY.json')['open_predicates']
oldby={r['relative']:r for r in oldmap['files']};pins={r['path']:r for r in profile['inputs']};oldpins={r['path']:r for r in old['inputs']}
assert len(context['Rust_files'])==len(oldby)==119 and {r['relative'] for r in context['Rust_files']}==set(oldby)
root=Path(context['context_root']);crate=Path(context['crate_entry']['path']);rustroot=Path(context['Rust_source_root']);assert rustroot==root/'kernel/rust' and crate==rustroot/'lib.rs'
checked=[]
for row in context['Rust_files']:
 assert row['original']['sha256']==row['snapshot']['sha256'] and row['original']['bytes']==row['snapshot']['bytes']
 expected=oldby[row['relative']]
 # Old source map names its actual source snapshot by postimage or snapshot.
 priorrefs=[v for v in expected.values() if isinstance(v,dict) and 'sha256' in v]
 assert any(r['sha256']==row['snapshot']['sha256'] and r['bytes']==row['snapshot']['bytes'] for r in priorrefs)
 assert Path(row['snapshot']['path'])==rustroot/row['relative'] and ref(row['snapshot']['path'])==row['snapshot']
 assert pins[row['snapshot']['path']]==row['snapshot'];checked.append(dict(relative=row['relative'],bytes=row['snapshot']['bytes'],sha256=row['snapshot']['sha256']))
actual114=read(context['accepted_actual114_source_profile']['path']);assert context['source6153']==actual114['inputs']['source6153']
external=[]
literals=re.findall(r'#\[path\s*=\s*"([^"]+)"\]',crate.read_text());assert set(literals)=={r['import_literal'] for r in context['external_relative_modules']} and len(literals)==3
for row in context['external_relative_modules']:
 dest=(crate.parent/row['import_literal']).resolve();assert dest==root/row['relative_to_context_root'] and str(dest)==row['snapshot']['path']
 assert row['genuine_source']['sha256']==row['snapshot']['sha256'] and row['genuine_source']['bytes']==row['snapshot']['bytes']
 assert Path(row['genuine_source']['path'])==Path(context['source6153'])/row['relative_to_context_root']
 assert ref(row['genuine_source']['path'])==row['genuine_source'] and ref(dest)==row['snapshot'] and pins[str(dest)]==row['snapshot']
 # Three concrete restored modules, no generic dependency parser or wider walk.
 text=dest.read_text();assert not re.search(r'#\[path\s*=|include(?:_bytes|_str)?!\s*\(',text)
 external.append(row)
assert sorted(r['snapshot']['bytes'] for r in external)==[4354,14227,17839]
assert sum(r['active_in_current_profile'] for r in external)==2

# Exact path-only argv adaptation; flags/provider/cfg/C-file environment unchanged.
newout=profile['leaves'][0]['output'];oldout=old['leaves'][0]['output'];mapping={oldout:newout,str(P/'rust-subtree/lib.rs'):str(crate),str(OLD/'qualify_changed_objects.py'):str(Q/'qualify_changed_objects.py'),str(P/'FIXED-CPP-CONTROLS.NOT-GRANTED.json'):str(Q/'FIXED-CPP-CONTROLS.NOT-GRANTED.json')}
deltas=[]
for i,(a,b) in enumerate(zip(old['commands'],profile['commands'])):
 expected=[]
 for value in a['argv']:
  for before,after in mapping.items():value=value.replace(before,after)
  expected.append(value)
 assert b['argv']==expected,(i,'non-path argv change')
 assert b['cwd']==a['cwd'] and b['purpose']==a['purpose'] and b['leaf']==a['leaf']
 deltas.append(dict(command=i,changed_argument_positions=[j for j,(x,y) in enumerate(zip(a['argv'],b['argv'])) if x!=y]))
for key in ['goal','fixed_deadline_UTC','fixed_cutoffs','resources','host_growth_reserve_bytes','scope_limit','internal_and_capture_bound_bytes']:assert profile[key]==old[key]
assert profile['capture_root']!=old['capture_root'] and newout!=oldout and not Path(profile['capture_root']).exists() and not Path(newout).exists()
oldcpp=read(P/'FIXED-CPP-CONTROLS.NOT-GRANTED.json');newcpp=read(Q/'FIXED-CPP-CONTROLS.NOT-GRANTED.json');assert oldcpp.keys()==newcpp.keys()
for a,b in zip(oldcpp['commands'],newcpp['commands']):
 assert all(a[k]==b[k] for k in a if k!='argv') and [v.replace(oldout,newout) for v in a['argv']]==b['argv']
assert len(newcpp['commands'])==8
oldsrc=(OLD/'qualify_changed_objects.py').read_text();newsrc=(Q/'qualify_changed_objects.py').read_text();normalized=newsrc
for prefix in ['RUST_CONTEXT_ROOT=','CURRENT_PROPOSAL=','CURRENT_CONTEXT=']:normalized='\n'.join(line for line in normalized.split('\n') if not line.startswith(prefix))
normalized=normalized.replace("str(RUST_CONTEXT_ROOT/relative)","str(D/'rust-subtree'/relative)").replace('proposal=read(CURRENT_PROPOSAL)',"proposal=read(D/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json')").replace("read(CURRENT_CONTEXT)['Rust_files']","read(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')['files']")
assert normalized==oldsrc
runner=E/'ordinary-host-new12h-runner-source-1/run_new12h_host.py';tree=ast.parse(runner.read_text());ns=dict(Path=Path,hashlib=hashlib,json=json,THREAD='01a17e6f-112f-7660-8771-85d15e07a26c',CUTOFFS=[1793165769.0,947874.5689514667,963213.6960030915]);exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'need','validate_profile'}],type_ignores=[]),'retained ordinary metadata validator only','exec'),ns);ns['validate_profile'](profile)
fail=read(Q/'PRESERVED-FIRST-HOST-FAILURE.json');assert fail['passing_compiler_prefix']==0 and fail['returncode']==1 and fail['commands1_to6_unrun'] and fail['direct_child_joined'] and fail['group_absent'] and fail['closed_streams']
for key in ['original_profile','original_results','original_first_failure','consumed_grant','original_stderr','original_stdout']:assert ref(fail[key]['path'])==fail[key]
results=read(fail['original_results']['path']);assert len(results['results'])==1 and results['results'][0]['join']['returncode']==1
assert 'couldn\'t read' in Path(fail['original_stderr']['path']).read_text() and '../../host-kernel/native-rust/abi/vdso.rs' in Path(fail['original_stderr']['path']).read_text()
report=dict(scope=__doc__.splitlines()[0],decision='PASS_SOURCE_GENUINE_RELATIVE_MODULE_CONTEXT_CORRECTION_ONLY',independent=True,reviewer='/root/current110_execution_review',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),ready=ref(Q/'SOURCE-READY.json'),profile=ref(Q/'PROFILE.NOT-GRANTED.json'),context=ref(Q/'CLOSED-RUST-MODULE-CONTEXT.json'),prior_positive_source_review=ref(prior),preserved_original_failure=ref(Q/'PRESERVED-FIRST-HOST-FAILURE.json'),original_failure_code=1,passing_compiler_prefix=0,commands1_to6_unrun=True,Rust119_new_context_snapshot_checks=checked,restored_genuine_modules=external,command_path_deltas=deltas,
findings=['The same119 private Rust source snapshots retain exact bytes and relative namespace under context-root/kernel/rust. The new snapshot manifest was validated once; old shared119 sources/canonical inventory were not rehashed.','All three literal lib #[path] references resolve within the new private context. Active vdso17839B/zero_pages4354B and disabled sysfs fixture14227B match genuine accepted114 source6153 exactly; these three concrete files have no additional path/include macro dependencies. No ABI mirror, stub, provider/cfg/body change or visibility widening is introduced.','All seven argv changes are exact compiler-entry/output/helper/CPP-plan path substitutions. Every existing environment assignment including process C filename/defaultflags0, cfg/provider list, compiler option, C source/ABI fixture and link scope remains unchanged. Eight CPP cases retain exact source/feature/diagnostic expectations, only output paths change.','Qualifier differs only in three explicit context/proposal constants and their corresponding metadata path substitutions. Reversing those exact substitutions reproduces prior a9f-reviewed reader bytes, preserving exact46/102/148 registry provenance, ABI/config/callback checks, defaultON unsupported-variant limits and folded-consumer OPEN/exit2 policy.','Fresh output/capture are absent and disjoint; exact6e98 pure validate_profile passes. CPU6/job1/AS2GiB/CPU60/FSIZE64MiB/CORE0/90s,4GiB growth reserve and all existing fixedclock/account/admission/resource controls remain unchanged.','Original actual Rust command0 return1/.283065972s missing genuine outer vdso module is preserved with positive join/group absent/closed streams; no passed compiler prefix exists. A future Root grant may retry corrected command0 and run previously unrun1..6. No old GLOBAL32 qualification prefix is replayed.'],
open_predicates=['Fresh Root CPU6 exclusion/current account/resources/fresh nonce and ordinary grant remain necessary; a concurrent existing ordinary job is not authorized by this source receipt.','All actual compiler/partial-link/CPP/object/consumer results remain unrun for this correction. Repeated same context failure follows preserved convergence escalation rather than another automatic retry.','Missing folded named references require exact actual instruction/dataflow supplement; all-profile object/link/native/default production and whole-file credit remain OPEN.'],blocking_findings=[],runtime_authority=None,actual_compilers=0,actual_CPP=0,actual_qualifier_main=0,guard_or_resource_queries=0,workloads=0,canonical_mutations=0,passed_GLOBAL32_prefix_replays=0)
out=D/'INDEPENDENT-SOURCE-PROFILE-REVIEW.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(decision=report['decision'],receipt=ref(out),Rust_body_changes=0,restored_modules=3,blocking_findings=0)))
