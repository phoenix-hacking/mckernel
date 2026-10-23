"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source/metadata preparation only; no imports of runtime owner or probes.
"""
from pathlib import Path
import ast,copy,hashlib,json
D=Path(__file__).resolve().parent
S=D.parent/'actual-session-staging-1/expert-composite-binding-1/bounded-correction-1/source'
OLD=Path('/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1/current110-variant-1/source')
E=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/capacity-binding-1/producer-implementation-1/real-consumer-1/session-staging-preparation-1/runtime-coherent-source-integration-1')
R=D/'source';R.mkdir()
def ref(p):
 b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'size':len(b)}
def write(name,value):
 b=(json.dumps(value,indent=2)+'\n').encode();(D/name).write_bytes(b);return ref(D/name)
def assignments(text):
 result={}
 for n in ast.parse(text).body:
  if isinstance(n,ast.Assign):
   for t in n.targets:
    if isinstance(t,ast.Name) and t.id in ('SELF','RUNNER','SOURCE_HASHES','EXTRA_READONLY','REPO','SCRATCH'):
     result[t.id]=(n,ast.literal_eval(n.value))
 return result
names=('composite_module_binding.py','long_transport.py','native_diagnostic.py','native_diagnostic_backend.py','native_diagnostic_container_owner.py','native_diagnostic_runner.py','p12_long_session.py','qmp_capture.py','repaired_image_authority.py','CURRENT68-SDK5-AUTHORITY-LINKS.json')
for name in names:(R/name).write_bytes((S/name).read_bytes())
links=json.loads((R/'CURRENT68-SDK5-AUTHORITY-LINKS.json').read_text())
proofs={}
def get(row):
 p=Path(row['path']);b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256'] and len(b)==row['bytes'];proofs[str(p)]={'path':str(p),'sha256':row['sha256'],'size':len(b)};return json.loads(b)
top={name:get(row) for name,row in links['proofs'].items()}
get(top['SDK5_acceptance']['actual_reads']);get(top['SDK5_acceptance']['owner_receipt'])
get(top['image_build_acceptance']['producer_receipt']);get(top['launcher_build_acceptance']['receipt']);get(top['current235_acceptance']['physical_acceptance'])
closure=json.loads((S.parent/'FINAL-EXPERT-CONSUMER-CLOSURE.json').read_text())
manifest=closure['validated_existing_inputs']['manifest'];overlay=closure['validated_existing_inputs']['overlay_manifest']
manifest_doc=json.loads(Path(manifest['path']).read_text())
oldtext=(R/'native_diagnostic_container_owner.py').read_text();a=assignments(oldtext)
source_hashes={path:digest for path,digest in a['SOURCE_HASHES'][1].items() if Path(path).parent!=OLD}
historical_count=len(source_hashes)
# SELF is checked by the real owner_sha contract; do not create a self-hash cycle.
for name in names:
 if name!='native_diagnostic_container_owner.py':row=ref(R/name);source_hashes[row['path']]=row['sha256']
for row in proofs.values():source_hashes[row['path']]=row['sha256']
for row in (manifest,overlay):source_hashes[row['path']]=row['sha256']
extras=[p for p in a['EXTRA_READONLY'][1] if p!=str(OLD)]
required=[str(R),str(Path(manifest['path']).parent),'/home/holden/mckernel-work/host-preparation/p12-long-mixed-apps-20261023-1',*[row['path'] for row in proofs.values()]]
# Avoid duplicate/subtree mounts when the original REPO/SCRATCH/readonly roots
# already expose a source. This does not change ownership or mount policy.
def covered(path,roots):
 p=Path(path);return any(p==Path(root) or Path(root) in p.parents for root in roots)
for path in required:
 if not covered(path,[a['REPO'][1],a['SCRATCH'][1],*extras]):extras.append(path)
updates={'RUNNER':str(R/'native_diagnostic_runner.py'),'SELF':str(R/'native_diagnostic_container_owner.py'),'SOURCE_HASHES':source_hashes,'EXTRA_READONLY':extras}
lines=oldtext.splitlines(keepends=True)
for name in sorted(updates,key=lambda name:a[name][0].lineno,reverse=True):
 n=a[name][0];lines[n.lineno-1:n.end_lineno]=[name+' = '+repr(updates[name])+'\n']
newtext=''.join(lines).replace("    source = '"+str(OLD/'native_diagnostic.py')+"'","    source = '"+str(R/'native_diagnostic.py')+"'")
(R/'native_diagnostic_container_owner.py').write_text(newtext)
# Bounded AST source guards: the only function-body change is diagnostic path
# literal in bound_manifest. All lifecycle/acquisition/cleanup/command bodies
# are byte-semantic identical; no runtime code is executed by this preparation.
def functions(text):
 return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
f0=functions(oldtext);f1=functions(newtext);assert set(f0)==set(f1)
assert [name for name in f0 if f0[name]!=f1[name]]==['bound_manifest']
before=next(n for n in ast.parse(oldtext).body if isinstance(n,ast.FunctionDef) and n.name=='bound_manifest')
after=next(n for n in ast.parse(newtext).body if isinstance(n,ast.FunctionDef) and n.name=='bound_manifest')
for n in ast.walk(before):
 if isinstance(n,ast.Constant) and n.value==str(OLD/'native_diagnostic.py'):n.value=str(R/'native_diagnostic.py')
assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
for name in names:
 if name!='native_diagnostic_container_owner.py':assert (R/name).read_bytes()==(S/name).read_bytes()
for path in [*source_hashes,manifest['path'],*[row['path'] for row in manifest_doc['artifacts'].values()],*[row['path'] for row in manifest_doc['modules']],*[row['path'] for row in manifest_doc['staging'].values()],*[a['payload']['path'] for a in manifest_doc['pair']['apps']]]:
 assert covered(path,[a['REPO'][1],a['SCRATCH'][1],*extras]),'unmounted consumed path '+path
bindings=write('COHERENT-SOURCE-BINDINGS.json',{'scope':__doc__,'inputs':[ref(S/name) for name in names],'outputs':[ref(R/name) for name in names],'authority_proof_closure':list(proofs.values()),'saved_manifest':manifest,'saved_base':closure['validated_existing_inputs']['base_archive'],'saved_capsule':closure['validated_existing_inputs']['derived_archive'],'saved_overlay_manifest':overlay,'historical_source_hash_rows_reused_without_rehash':historical_count,'total_SOURCE_HASHES':len(source_hashes),'readonly_roots':extras,'REPO':a['REPO'][1],'SCRATCH':a['SCRATCH'][1],'all_consumed_literal_paths_readonly_covered':True,'source_only_AST_lifecycle_guards':True,'actual_runtime_functions_executed':False})
write('SOURCE-DIFF-SCOPE.json',{'scope':__doc__,'owner_before':ref(S/'native_diagnostic_container_owner.py'),'owner_after':ref(R/'native_diagnostic_container_owner.py'),'only_changed_constants':list(updates),'only_changed_function':'bound_manifest diagnostic source literal only','all_other_functions_and_classes_AST_unchanged':True,'runner_byte_unchanged':True,'accepted_native_88a07d62_composite_eb44f800_repaired_63db0419_links14bc2034_bytes_unchanged':True,'source_binding':bindings,'old_current110_142_cohorts_written':False,'producer_apps_archives_written':False,'runtime_admission':None})
for p in D.rglob('*'):
 if p.is_file():
  q=E/p.relative_to(D);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
print(json.dumps({'source':str(R),'owner':ref(R/'native_diagnostic_container_owner.py'),'SOURCE_HASHES':len(source_hashes),'historical_reused':historical_count,'proofs':len(proofs),'readonly_roots':len(extras)}))
