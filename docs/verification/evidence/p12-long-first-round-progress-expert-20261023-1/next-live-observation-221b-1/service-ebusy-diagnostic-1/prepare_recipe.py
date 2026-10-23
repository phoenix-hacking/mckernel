# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,ast
P=Path(__file__).resolve().parent;F=P/'fixture';O=P/'fixture-output-1'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
b=json.loads((P/'SOURCE-BINDINGS.json').read_text());r='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc';assert pin(Path(r))['sha256']=='028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1'
for row in b['changes'].values():assert pin(Path(row['selected_original']['path']))==row['selected_original'] and pin(Path(row['canonical_preimage']['path']))==row['canonical_preimage'] and pin(Path(row['private_postimage']['path']))==row['private_postimage']
for row in b['unmodified_error_ownership_modules'].values():assert pin(Path(row['path']))==row
# Exact pure original predicate remains; no quarantine/admit module is edited.
def function(s,marker):
 lines=s.splitlines(keepends=True);hits=[i for i,x in enumerate(lines) if x.lstrip().startswith(marker)];assert len(hits)==1;(a,)=hits;indent=len(lines[a])-len(lines[a].lstrip());end=next(i for i in range(a+1,len(lines)) if lines[i].rstrip()==' '*indent+'}');return ''.join(lines[a:end+1]).rstrip('\n')
orig=Path(b['changes']['sysfs_memory.rs']['selected_original']['path']).read_text();new=(P/'source/sysfs_memory.rs').read_text();assert function(orig,'fn conflicts(')==function(new,'fn conflicts(') and function(orig,'fn tag(')==function(new,'fn tag(')
for x in ['prepare_source.py','prepare_fixture.py','prepare_recipe.py']:ast.parse((P/x).read_text())
commands=[dict(name='00-pure-actual-body-Rust-compile',argv=[r,'--edition=2021','-C','opt-level=2','-C','panic=abort','-C','codegen-units=1',str(F/'diagnostic.rs'),'-o',str(O/'diagnostic-fixture')]),dict(name='01-functional-pure-error-context-fixture',argv=[str(O/'diagnostic-fixture')])]
recipe=dict(scope=b['scope'],status='ROOT_GRANTED_ORDINARY_CPU0_PURE_DIAGNOSTIC_FIXTURE_NOT_YET_EXECUTED',authority='Root explicit CPU0ordinary onejob2GiBAS60CPU90wall+6 FSIZE32MiBNOFILE256core0 Rust1.92CGU1/2MiBstack+h990807acceptedstophandlers. Diagnostic only; no root/SDKmodule/guest/native/canonical execution.',profile=dict(CPU=0,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,RUST_MIN_STACK=2097152),tools={r:pin(Path(r))},source_bindings=pin(P/'SOURCE-BINDINGS.json'),fixture_bindings=pin(P/'FIXTURE-SOURCE-BINDINGS.json'),source_files={str(x.relative_to(P)):pin(x) for x in [*F.iterdir(),P/'source/smp_service.rs',P/'source/sysfs_memory.rs',P/'PRIVATE-DIAGNOSTIC.patch'] if x.is_file()},commands=commands,expected_output='PASS memory_pairs=8195 conflict_bucket_masks=256 origins=10 observer_before_quarantine=1 errors_claims_callcounts_unchanged=1 budgets=16; HOST_PRIMITIVES_MODELED_NO_NATIVE',preserved_original_conflicts_and_tag_functions=True,models='Kernel Arc/Mutex/Vec, memoryaddress mapping, fail_service/application and Remote receiver only. Actual source bodies/Request decoder/getters/quarantine branch extracted. This is not kerneltype/layout/runtime/diagnosticcause proof.',canonical_unchanged=True)
(P/'EXACT-ORDINARY-FIXTURE-RECIPE.GRANTED.json').write_text(json.dumps(recipe,indent=2)+'\n')
print(json.dumps(dict(recipe=pin(P/'EXACT-ORDINARY-FIXTURE-RECIPE.GRANTED.json'),postimages={k:v['private_postimage'] for k,v in b['changes'].items()})))
