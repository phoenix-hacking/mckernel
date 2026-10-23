"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Derive candidate8 source/producer/consumer metadata from frozen7; no build.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1');B=H/'production-combined-7/default-image-preparation-1';N=H/'production-combined-8/default-image-preparation-1';S=N/'source-materialization-attempt-1'
AUTH=R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/next-memory-bridge-rust-20261023-1/CANONICAL-INTEGRATION.json'
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(name,raw):
 if not isinstance(raw,bytes):raw=(json.dumps(raw,indent=2,sort_keys=True)+'\n').encode()
 for d in (E,N):
  with (d/name).open('xb') as f:f.write(raw)
 return ref(N/name)
def controller(name,old,new):
 ast.parse(new);o=save(name,new.encode());save(name+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='frozen7/'+name,tofile='future8/'+name)).encode());return o
N.mkdir(parents=True,mode=0o700)
a=json.loads(AUTH.read_text());assert a['status']=='CANONICAL_SOURCE_INTEGRATED_BOUNDED_SLICE' and ref(AUTH)['sha256']=='c07d47d1cf2eaf12ab14354fa92584e0d202d08898a75c2a6e46326ccf5d68e5'
POST={row['path']:row['sha256'] for row in a['after']};pre={row['path']:row['sha256'] for row in a['before']};assert len(POST)==3
base=json.loads((B/'source-materialization-attempt-1/source-inputs.json').read_text());doc=copy.deepcopy(base);delta=[]
for rel,h in POST.items():
 assert ref(R/rel)['sha256']==h and base['repository_files'][rel]==pre[rel]
 delta.append(dict(path=rel,before_sha256=pre[rel],after_sha256=h));doc['repository_files'][rel]=doc['materialized_repository_files'][rel]=h
basehash='1ff94d6e48bb3b694d09ac467fc1dd630d471983fcc24335b2cd5c3c85aaf48b'
derivation=dict(base_manifest_canonical_sha256=basehash,base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay'])
doc['source_derivative_sha256']=sha(canon(derivation));doc['latest_memory_callback_overlay']=derivation
mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canon(mat));mh=sha(canon(doc))
old=(B/'materialize_source.py').read_text();lines=old.splitlines(True);values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(basehash),'POST':repr(POST)}
for n in reversed(ast.parse(old).body):
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:
  name=n.targets[0].id;lines[n.lineno-1:n.end_lineno]=[name+' = '+values[name]+'\n']
new=''.join(lines).replace("os.sched_getaffinity(0) == {0}","os.sched_getaffinity(0) == {6}").replace('ordinary CPU0 grant required','ordinary CPU6 grant required').replace("authority['status'] == 'PARTIAL_CANONICAL_SOURCE_INTEGRATED' and {row['path']:row['sha256'] for row in authority['files']}","authority['status'] == 'CANONICAL_SOURCE_INTEGRATED_BOUNDED_SLICE' and {row['path']:row['sha256'] for row in authority['after']}")
producer=controller('materialize_source.py',old,new)
old=(B/'native_rust_exact_build_offline.py').read_text();assert old.count(basehash)==1;prov=controller('native_rust_exact_build_offline.py',old,old.replace(basehash,mh))
old=(B/'native_rust_exact_mckernel_image_offline.py').read_text();new=old.replace(ref(B/'native_rust_exact_build_offline.py')['sha256'],prov['sha256'])
for row in delta:assert new.count(row['before_sha256'])==1;new=new.replace(row['before_sha256'],row['after_sha256'])
new=new.replace("'x86_init_text_map_kernel_start_bridge')","'x86_init_text_map_kernel_start_bridge', 'x86_init_text_end_bridge')",2)
anchor="    _fail(not any(row[-2] == 'U' for row in rows(rust_symbols, getter)), 'M14 textmap unresolved Rust getter')"
addition="""
    end_getter = 'x86_init_text_end_bridge'
    _fail(not any(row[-2] in ('T', 't') for row in rows(memory_symbols, end_getter)),
          'M14 text-end original C getter selected')
    for text in (rust_symbols, image_symbols):
        found = rows(text, end_getter)
        _fail(len(found) == 1 and found[0][-2] == 'T', 'M14 text-end unique Rust getter')
    found = rows(rust_symbols, '_end')
    _fail(len(found) == 1 and found[0][-2] == 'U', 'M14 text-end Rust linker-address consumer')
    found = rows(image_symbols, '_end')
    _fail(len(found) == 1 and found[0][-2].upper() != 'U',
          'M14 final linker _end must be defined; no type/width assumption')
"""
assert new.count(anchor)==1;new=new.replace(anchor,anchor+addition,1)
new=new.replace("geometry='x86_map_kernel_start_geometry', immutable_geometry_bytes=8,","geometry='x86_map_kernel_start_geometry', immutable_geometry_bytes=8,\n                text_end_getter='x86_init_text_end_bridge', Rust_end_import=True, final_end_defined=True,",1)
driver=controller('native_rust_exact_mckernel_image_offline.py',old,new)
# Source constants only; no compiler/test/driver execution.
values={}
for node in ast.parse(new).body:
 if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('M14_IDLE_IMPORTS','M14_MEMORY_IMPORTS','M14_C_RETIRED_MEMORY_BODIES','M14_RUST_EXPORTS'):
  values[node.targets[0].id]=eval(compile(ast.Expression(node.value),'constant-source-binding','eval'),{'__builtins__':{}},values)
assert len(values['M14_MEMORY_IMPORTS'])==4 and len(values['M14_RUST_EXPORTS'])==16 and len(set(values['M14_RUST_EXPORTS']))==16 and 'x86_init_text_end_bridge' in values['M14_C_RETIRED_MEMORY_BODIES']
save('SOURCE-CONSUMER-JOIN.PREPARED.json',dict(scope=__doc__,status='SOURCE_METADATA_PREPARED_ONLY',canonical_integration=ref(AUTH),source_ABI_review=ref(AUTH.parent/'INDEPENDENT-SOURCE-ABI-ACCEPTANCE.ROOT-RECORD.json'),actual_private_Rust_receipt=ref(AUTH.parent/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json'),changed_source_files=delta,predicted_manifest_sha256=mh,predicted_manifest_bytes=len(canon(doc)),source_derivative_sha256=doc['source_derivative_sha256'],materialization_sha256=doc['materialization_sha256'],producer=producer,provenance=prov,driver=driver,preserved_source_entries=6959,preserved_symlinks=49,preserved_all_other_sources_modes_metadata=True,real_C_imports=values['M14_MEMORY_IMPORTS'],retired_C_bodies=values['M14_C_RETIRED_MEMORY_BODIES'],Rust_final_providers=values['M14_RUST_EXPORTS'],text_end_contract='PUBLIC C getter excluded; actualRustgetterT+Rust_endU; finalgetterT+_enddefined(any linkerdefined kind/size). C_end may remain; no invented Cgetter import.',prior_guard_failure='candidate6 erroneous fictionalCimport995b retained; corrected7b9 descendants used',actual_materialization=None,actual_pure=None,actual_whole_C_TU=None,actual_defaultlink=None,actual_native=None))
print(json.dumps(dict(manifest=mh,producer=producer,driver=driver,provenance=prov),sort_keys=True))
