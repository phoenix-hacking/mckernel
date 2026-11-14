# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import pathlib,json,hashlib,difflib,shutil
P=pathlib.Path(__file__).resolve().parent; R=pathlib.Path('/home/holden/mckernel'); E=R/'docs/verification/evidence/compute-process-next-body-cutover-20261023-1'
def ident(p):
 b=p.read_bytes(); return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
for p in [P/'prepare_source.py',P/'source/kernel/rust/sched_helpers.rs',P/'fixture/actual.rs',P/'fullcrate-preparation-1/source/kernel/rust/sched_helpers.rs']:
 s=p.read_text(); assert s.count('static time_sharing: CInt;')==1; p.write_text(s.replace('static time_sharing: CInt;','static mut time_sharing: CInt;'))
rels=['kernel/process.c','kernel/rust/sched_helpers.rs','kernel/rust/tests/run_equivalence.sh']
patch=''
for rel in rels:
 patch+=''.join(difflib.unified_diff((R/rel).read_text().splitlines(True),(P/'source'/rel).read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel,n=4))
(P/'PRIVATE-PRODUCTION.patch').write_text(patch)
bind=json.loads((P/'SOURCE-BINDINGS.json').read_text()); bind['outputs']={rel:ident(P/'source'/rel) for rel in rels}; bind['patch']=ident(P/'PRIVATE-PRODUCTION.patch'); (P/'SOURCE-BINDINGS.json').write_text(json.dumps(bind,indent=2)+'\n')
recipepath=P/'NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json'; recipe=json.loads(recipepath.read_text()); recipe['source_inputs']['kernel/rust/sched_helpers.rs']['private']=ident(P/'fullcrate-preparation-1/source/kernel/rust/sched_helpers.rs'); recipepath.write_text(json.dumps(recipe,indent=2)+'\n')
leafpath=P/'NEXT-LEAF-RECIPE.NOT-EXECUTED.json'; leaf=json.loads(leafpath.read_text()); leaf['files']={str(p.relative_to(P)):ident(p) for p in (P/'fixture').iterdir() if p.is_file()}; leafpath.write_text(json.dumps(leaf,indent=2)+'\n')
c=(P/'source/kernel/process.c').read_text(); rs=(P/'source/kernel/rust/sched_helpers.rs').read_text(); original=(P/'ORIGINAL-set_timer.c').read_text().rstrip()
checks={
 'fallback_exact_original_body': '#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+original+'\n#endif' in c,
 'one_C_body_in_fallback':c.count('void set_timer(int runq_locked)\n{')==1,
 'one_actual_Rust_export':rs.count('pub unsafe extern "C" fn set_timer(')==1,
 'mutable_C_global_binding':'static mut time_sharing: CInt;' in rs,
 'existing_provider_body_unchanged':rs[rs.index('pub unsafe extern "C" fn timer_set_timer_body_result('):rs.index('#[repr(C)]\npub struct SchedIdleOffsets')] == (R/'kernel/rust/sched_helpers.rs').read_text().split('pub unsafe extern "C" fn timer_set_timer_body_result(',1)[1].split('#[repr(C)]\npub struct SchedIdleOffsets',1)[0].join(['pub unsafe extern "C" fn timer_set_timer_body_result(','']),
 '78_input_production_recipe':len(recipe['source_inputs'])==78,
 'fixture_reuses_actual_wrapper':rs.split('pub unsafe extern "C" fn set_timer(',1)[1].split('\n#[no_mangle]',1)[0] in (P/'fixture/actual.rs').read_text(),
 'no_canonical_change_since_binding':all(ident(R/rel)==bind['source_inputs'][rel] for rel in rels),
}
assert all(checks.values()), checks
report=dict(scope=leaf['scope'],status='PASS_SOURCE_ONLY',checks=checks,compiled=False,whole_C_TU_default_kernel_native='OPEN')
(P/'SOURCE-PREPARATION-CHECK.json').write_text(json.dumps(report,indent=2)+'\n')
for path in P.iterdir():
 if path.is_file(): shutil.copyfile(path,E/path.name)
for dirname in ['source','fixture']:
 for path in (P/dirname).rglob('*'):
  if path.is_file(): dst=E/path.relative_to(P); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,dst)
print(json.dumps({n:ident(P/n) for n in ['SOURCE-BINDINGS.json','PRIVATE-PRODUCTION.patch','SOURCE-PREPARATION-CHECK.json','NEXT-LEAF-RECIPE.NOT-EXECUTED.json','NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json']}))
