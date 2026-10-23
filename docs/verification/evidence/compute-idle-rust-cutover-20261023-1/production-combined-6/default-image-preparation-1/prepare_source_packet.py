"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Metadata/controller derivation only. Never invoke materialization/compilers here.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1')
B=H/'production-combined-5/default-image-successor-1';N=H/'production-combined-6/default-image-preparation-1';S=N/'source-materialization-attempt-1'
OLD=R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/production-combined-5/default-image-successor-1'
AUTH=R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/init-large-page-bridge-rust-20261023-1/CANONICAL-BRIDGE-INTEGRATION.json'
def canon(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def save(n,b):
 if not isinstance(b,bytes):b=(json.dumps(b,indent=2,sort_keys=True)+'\n').encode()
 for d in (E,N):
  with (d/n).open('xb') as f:f.write(b)
 return ref(N/n)
def controller(n,old,new):
 ast.parse(new);out=save(n,new.encode());save(n+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=str(B/n),tofile=str(N/n))).encode());return out
N.mkdir(parents=True,mode=0o700)
a=json.loads(AUTH.read_text());assert a['status']=='PARTIAL_CANONICAL_SOURCE_INTEGRATED'
POST={r['path']:r['postimage_sha256'] for r in a['changed_files']}
assert len(POST)==3
base=json.loads((B/'source-materialization-attempt-1/source-inputs.json').read_text());doc=copy.deepcopy(base);delta=[]
for rel,h in POST.items():
 assert ref(R/rel)['sha256']==h
 assert base['repository_files'][rel]==next(row['preimage_sha256'] for row in a['changed_files'] if row['path']==rel)
 delta.append(dict(path=rel,before_sha256=base['repository_files'][rel],after_sha256=h));doc['repository_files'][rel]=doc['materialized_repository_files'][rel]=h
basehash='b47cf0f2a65aa90f2e010d717bf381c85adf063b68951fd8e53682cb87f27be6'
derivation=dict(base_manifest_canonical_sha256=basehash,base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay'])
doc['source_derivative_sha256']=sha(canon(derivation));doc['latest_memory_callback_overlay']=derivation
mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canon(mat));mh=sha(canon(doc))
old=(OLD/'materialize_source.py').read_text();lines=old.splitlines(True)
values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(basehash),'POST':repr(POST)}
for node in reversed(ast.parse(old).body):
 if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in values:
  name=node.targets[0].id;lines[node.lineno-1:node.end_lineno]=[name+' = '+values[name]+'\n']
new=''.join(lines).replace("authority['status'] == 'CANONICAL_TWO_FILE_SOURCE_INTEGRATION_ONLY' and {row['path']:row['postimage_sha256'] for row in authority['integrated']} == POST","authority['status'] == 'PARTIAL_CANONICAL_SOURCE_INTEGRATED' and {row['path']:row['postimage_sha256'] for row in authority['changed_files']} == POST")
producer=controller('materialize_source.py',old,new)
old=(B/'native_rust_exact_build_offline.py').read_text();assert old.count(basehash)==1
prov=controller('native_rust_exact_build_offline.py',old,old.replace(basehash,mh))
old=(B/'native_rust_exact_mckernel_image_offline.py').read_text();new=old.replace('cce6a9a98c4775e263dc1c0efe2ac6d432c521b847d340c79356b4e853971d7d',prov['sha256'])
for row in delta:
 if row['path']!='kernel/rust/tests/run_equivalence.sh':new=new.replace(row['before_sha256'],row['after_sha256'])
needle='M14_SOURCE_PINS = {\n';new=new.replace(needle,needle+"    'kernel/rust/tests/run_equivalence.sh': '"+POST['kernel/rust/tests/run_equivalence.sh']+"',\n",1)
new=new.replace("'x86_clear_page_unmap_bridge', 'x86_clear_free_pages_user_bridge')","'x86_clear_page_unmap_bridge', 'x86_clear_free_pages_user_bridge',\n                      'x86_init_normal_set_large_bridge')",1)
needle="    page_unmap_proof = _validate_m14_page_unmap_contract(source_root, build, tools, env, timeout, command_rows, objects)"
addition="""    rust_undefined = _m14_observe([tools['tools']['nm']['path'], '-u', str(build/'kernel/rust/mckernel_rust.o')],
                                  'Rust-undefined', out, tools, env, timeout, command_rows)
    _fail(not any(line.split()[-1:] == ['x86_init_normal_set_large_bridge'] for line in rust_undefined.splitlines()),
          'M14 bridge unresolved in full production Rust object')
"""
assert new.count(needle)==1;new=new.replace(needle,addition+needle)
driver=controller('native_rust_exact_mckernel_image_offline.py',old,new)
# Exact accepted algorithms, thin schema, observer1MiB cap and toolchain unchanged.
save('SOURCE-AND-CONSUMER-DELTA.PREPARED.json',dict(scope=__doc__,status='SOURCE_METADATA_PREPARED_ONLY',canonical_integration=ref(AUTH),independent_source_ABI_review=ref(AUTH.parent/'INDEPENDENT-SOURCE-ABI-AND-PRIVATE-RUST-CONSUMER-ACCEPTANCE.json'),base_manifest=dict(path=str(B/'source-materialization-attempt-1/source-inputs.json'),sha256=basehash),changed_source_files=delta,preserved_source_entries=6959,preserved_symlinks=49,preserved_other_source_modes_kinds_metadata=True,predicted_manifest_sha256=mh,predicted_manifest_bytes=len(canon(doc)),source_derivative_sha256=doc['source_derivative_sha256'],materialization_sha256=doc['materialization_sha256'],materializer=producer,provenance=prov,driver=driver,driver_delta=['three source postimage pins (including harness) and provenance manifest binding','add bridge to existing memory imports: selected whole memoryTU preprocess C-body exclusion/external declaration; actualdefault C object unique U+relocation','add bridge to inherited Rust/final T gate via same memory import tuple:13existingexports preserved plus14th bridge','explicit actual fullRust object no bridgeU; final image existing all-unresolved-empty gate retained'],actual_next_checks=['actual selected whole arch/x86_64/kernel/memory.c GCC14 TU using exact newlygenerated compileDB row and default PUBLIC cfg','actual Rust fullcrate defaultproduction flags:14uniqueT and bridge noU','actualdefaultmemory.o bridge U+relocation and no C body selected; full finalimage bridge uniqueT and no unresolved','bound real selectedmemory.o + fullRust relocatable partiallink via accepted toolchain relocatablelink geometry if required before native; not yet executed'],actual_materialization=None,actual_request=None,actual_whole_C_TU=None,actual_default_link=None,actual_native=None,source_owner_namespace_preparation=None,no_retirement_credit=True))
save('MATERIALIZATION-COMMAND.PREPARED.json',dict(scope=__doc__,status='NOT_GRANTED_NOT_EXECUTED',argv=['/usr/bin/taskset','-c','0','/usr/bin/python3','-I','-B',str(N/'materialize_source.py')],materializer=producer,profile=dict(cpu=0,jobs=1,as_bytes=2147483648,cpu_seconds=60,wall_seconds=90,cleanup_seconds=6,fsize_bytes=33554432,nofile=256,core=0),source_growth_limit_bytes=268435456,capture_extra_bytes=16777216,host_floor_bytes=17179869184,scratch_floor_bytes=12884901888,grant=None,actual_result=None,requires='Root ordinary grant, capacity+fullgap/reserve boundary, reviewed owned990 capture adapter and exclusive source-materialization-attempt-1 parent; no build/root allowed.'))
print(json.dumps({'predicted_manifest_sha256':mh,'producer':producer,'driver':driver},sort_keys=True))
