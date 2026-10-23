"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source/metadata preparation only. No materializer, compiler or validator execution.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
R=Path('/home/holden/mckernel');E=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1')
B=H/'production-combined-6/default-image-preparation-1';N=H/'production-combined-7/default-image-preparation-1';S=N/'source-materialization-attempt-1'
AUTH=R/'docs/verification/evidence/compute-idle-rust-cutover-20261023-1/text-map-start-bridge-rust-20261023-1/CANONICAL-TEXTMAP-BRIDGE-INTEGRATION.json'
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=sha(b),bytes=len(b))
def save(n,b):
 if not isinstance(b,bytes):b=(json.dumps(b,indent=2,sort_keys=True)+'\n').encode()
 for d in (E,N):
  with (d/n).open('xb') as f:f.write(b)
 return ref(N/n)
def controller(n,old,new):
 ast.parse(new);out=save(n,new.encode());save(n+'.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='candidate6/'+n,tofile='candidate7/'+n)).encode());return out
N.mkdir(parents=True,mode=0o700)
a=json.loads(AUTH.read_text());assert a['status']=='PARTIAL_CANONICAL_SOURCE_INTEGRATED';POST={row['path']:row['sha256'] for row in a['files']};assert len(POST)==3
base=json.loads((B/'source-materialization-attempt-1/source-inputs.json').read_text());doc=copy.deepcopy(base);delta=[]
for rel,h in POST.items():
 assert ref(R/rel)['sha256']==h
 delta.append(dict(path=rel,before_sha256=base['repository_files'][rel],after_sha256=h));doc['repository_files'][rel]=doc['materialized_repository_files'][rel]=h
basehash='2c937f9311f1ff43da4cf6df3d26e03e759ab73d96b0d22fceee0fb23464f1e9'
derivation=dict(base_manifest_canonical_sha256=basehash,base_source_derivative_sha256=base['source_derivative_sha256'],canonical_integration_sha256=ref(AUTH)['sha256'],latest_memory_two_source_delta=delta,repository_files=doc['repository_files'],gitlinks=doc['gitlinks'],ihk_overlay=doc['ihk_overlay'])
doc['source_derivative_sha256']=sha(canon(derivation));doc['latest_memory_callback_overlay']=derivation
mat={k:doc[k] for k in ('source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks')};doc['materialization_sha256']=sha(canon(mat));mh=sha(canon(doc))
old=(B/'materialize_source.py').read_text();lines=old.splitlines(True);values={'OUT':'Path('+repr(str(S))+')','BASE':'Path('+repr(str(B/'source-materialization-attempt-1'))+')','AUTHORITY':'Path('+repr(str(AUTH))+')','BASE_CANONICAL_SHA':repr(basehash),'POST':repr(POST)}
for n in reversed(ast.parse(old).body):
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in values:
  name=n.targets[0].id;lines[n.lineno-1:n.end_lineno]=[name+' = '+values[name]+'\n']
new=''.join(lines).replace("{row['path']:row['postimage_sha256'] for row in authority['changed_files']}","{row['path']:row['sha256'] for row in authority['files']}")
producer=controller('materialize_source.py',old,new)
old=(B/'native_rust_exact_build_offline.py').read_text();assert old.count(basehash)==1;prov=controller('native_rust_exact_build_offline.py',old,old.replace(basehash,mh))
old=(B/'bounded-driver-correction-1/native_rust_exact_mckernel_image_offline.py').read_text();new=old.replace(ref(B/'native_rust_exact_build_offline.py')['sha256'],prov['sha256'])
for row in delta:assert new.count(row['before_sha256'])==1;new=new.replace(row['before_sha256'],row['after_sha256'])
new=new.replace("M14_C_RETIRED_MEMORY_BODIES = ('clear_range_old_action', 'x86_init_normal_set_large_bridge')","M14_C_RETIRED_MEMORY_BODIES = ('clear_range_old_action', 'x86_init_normal_set_large_bridge',\n                               'x86_init_text_map_kernel_start_bridge')",1)
new=new.replace("('page_unmap', 'x86_init_normal_set_large_bridge')","('page_unmap', 'x86_init_normal_set_large_bridge', 'x86_init_text_map_kernel_start_bridge')",1)
# Same accepted symbol-reader idiom as page_unmap R/U geometry checking.
extension="""def _m14_check_textmap_symbols(memory_symbols, rust_symbols, image_symbols):
    def rows(text, symbol):
        return [line.split() for line in text.splitlines() if line.split()[-1:] == [symbol]]
    getter = 'x86_init_text_map_kernel_start_bridge'
    geometry = 'x86_map_kernel_start_geometry'
    _fail(not rows(memory_symbols, getter), 'M14 textmap original C getter selected')
    for text in (rust_symbols, image_symbols):
        found = rows(text, getter)
        _fail(len(found) == 1 and found[0][-2] == 'T', 'M14 textmap unique Rust getter owner')
    for text in (memory_symbols, image_symbols):
        found = rows(text, geometry)
        _fail(len(found) == 1 and len(found[0]) == 4 and found[0][-2] == 'R' and
              int(found[0][1], 16) == 8, 'M14 textmap immutable LP64 geometry provider')
    found = rows(rust_symbols, geometry)
    _fail(len(found) == 1 and found[0][-2] == 'U', 'M14 textmap Rust geometry consumer')
    _fail(not any(row[-2] == 'U' for row in rows(rust_symbols, getter)), 'M14 textmap unresolved Rust getter')


def _validate_m14_textmap_contract(build, tools, env, timeout, command_rows, objects):
    out = build / 'm14-production'
    texts = []
    for path, label in ((Path(objects['arch/x86_64/kernel/memory.c']['path']), 'default-memory-textmap-ownership'),
                        (build/'kernel/rust/mckernel_rust.o', 'Rust-textmap-ownership'),
                        (build/'kernel/mckernel.img', 'image-textmap-ownership')):
        texts.append(_m14_observe([tools['tools']['nm']['path'], '-S', '-g', str(path)],
                                 label, out, tools, env, timeout, command_rows))
    _m14_check_textmap_symbols(*texts)
    return dict(getter='x86_init_text_map_kernel_start_bridge', C_getter_excluded=True,
                geometry='x86_map_kernel_start_geometry', immutable_geometry_bytes=8,
                native=False)


"""
anchor='def _validate_m14_source_pins(source_root):';assert new.count(anchor)==1;new=new.replace(anchor,extension+anchor,1)
anchor="    proof = dict(status='PASS_PINNED_FULLCRATE_DEFAULT_C_CONSUMERS_AND_FINAL_LINK_ONLY',";assert new.count(anchor)==1
new=new.replace(anchor,"    textmap_proof = _validate_m14_textmap_contract(build, tools, env, timeout, command_rows, objects)\n"+anchor,1)
new=new.replace('source_pins=M14_SOURCE_PINS, objects=objects, page_unmap_public_contract=page_unmap_proof, idle_imports=M14_IDLE_IMPORTS,','source_pins=M14_SOURCE_PINS, objects=objects, page_unmap_public_contract=page_unmap_proof, textmap_contract=textmap_proof, idle_imports=M14_IDLE_IMPORTS,',1)
driver=controller('native_rust_exact_mckernel_image_offline.py',old,new)
requestdelta=dict(source_root=str(S/'materialized-source'),source_manifest=str(S/'source-inputs.json'),source_manifest_sha256=mh,source_derivative_sha256=doc['source_derivative_sha256'],materialization_sha256=doc['materialization_sha256'],driver_path=driver['path'],driver_sha256=driver['sha256'],provenance_path=prov['path'],provenance_sha256=prov['sha256'])
save('CANDIDATE7-SOURCE-CONSUMER-JOIN.PREPARED.json',dict(scope=__doc__,status='SOURCE_AND_METADATA_ONLY_NOT_MATERIALIZED',base_manifest=dict(path=str(B/'source-materialization-attempt-1/source-inputs.json'),sha256=basehash),base_frozen_pure_request=dict(path=str(B/'next-build-preparation-1/image-request.PREPARED.json'),sha256='095b20a82a3477519ba933babe21fe256fa73c2b69613b7d12f97e95cf58b39e'),canonical_integration=ref(AUTH),source_ABI_review=ref(AUTH.parent/'INDEPENDENT-SOURCE-ABI-AND-PRIVATE-RUST-ACCEPTANCE.json'),actual_private_Rust_receipt=ref(AUTH.parent/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json'),changed_source_files=delta,preserved_source_entries=6959,preserved_tracked_symlinks=49,preserved_all_other_source_modes_kinds_metadata=True,predicted_manifest_sha256=mh,predicted_manifest_bytes=len(canon(doc)),producer=producer,provenance=prov,driver=driver,request_named_fields=requestdelta,source_identity=None,gitlink_manifest=None,actual_source_manifest=None,actual_request=None,actual_pure_consumer=None,actual_whole_C_TU=None,actual_default_link=None,actual_native=None,driver_expectations=['Preserve accepted13exports+normal-large bridge and four realCimports; never require normal-large C U/reloc','Actual selected whole memory.c GCC14PUBLIC compile excludes both bridge Cbodies','New textmap getter one Rust/finalT; noCgetter; exactimmutablegeometry8byteR inwholeC/final, RustobjectUgeometry; existing final allundefinedempty','Accepted Rust source getter consumes imported geometry and preservesbuildresolvedvalue; no invented numericMAP_KERNEL_START constant','15uniqueRust/finalexports: original13+normal-large+textmap; exactleafABI reviewed5bac and actual78inputRustf601 retained'],failure_history=['Originalcandidate6prepared995b fictional newbridge C-U expectation rejected before execution; corrected7b9 source retained and usedasbase; no newfailure/retry'],execution_authorized=False))
save('NEXT-OBSERVATIONS.NOT-EXECUTED.json',dict(scope=__doc__,status='NO_ORDINARY_GRANT_YET',materialization=dict(argv=['/usr/bin/taskset','-c','0','/usr/bin/python3','-I','-B',str(N/'materialize_source.py')],source=producer,profile=dict(cpu=0,jobs=1,AS_bytes=2147483648,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=33554432,NOFILE=256,core=0),max_HOST_source_growth_bytes=268435456,capture_extra_bytes=16777216),cheapest_meaningful_pure_validation=dict(algorithm='Reuse candidate6 prepare_and_validate.py namespace/request derivation plus exact complete owner._validate_request; exactAnaconda3.9.12, owned990 ASTloader with SIGTERM/INT/ALRM registration; noImageOwner.run/acquire',argv_template=['/usr/bin/taskset','-c','0','/home/holden/anaconda3/bin/python3','-I','-B',str(N/'next-build-preparation-1/prepare_and_validate.py')],profile=dict(cpu=0,jobs=1,AS_bytes=2147483648,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=33554432,NOFILE=256,core=0),requires='Actualmaterialization then exactowner/hash/gitlinksupplement/request and exclusivefreshHOSTattempt1 identities; allNULLnow'),root_heavy_build_release=None,compiler_defaultlink_native=None))
print(json.dumps({'producer':producer,'driver':driver,'predicted_manifest_sha256':mh},sort_keys=True))
