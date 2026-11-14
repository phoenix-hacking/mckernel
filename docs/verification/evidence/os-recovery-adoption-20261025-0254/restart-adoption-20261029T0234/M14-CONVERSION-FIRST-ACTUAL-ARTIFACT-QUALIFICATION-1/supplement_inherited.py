"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact inherited specialized-consumer/source/ABI/warning readback, no runtime.
"""
from pathlib import Path
import ast,struct,json,hashlib,re,collections
p=Path(__file__).resolve().parent/'inspect_conversion.py';nodes=[]
for node in ast.parse(p.read_bytes()).body:
 if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='proofs'for t in node.targets):break
 nodes.append(node)
context={'__file__':str(p)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p)+':READONLY_CONTEXT_ONLY','exec'),context);globals().update(context)
fn=own
special_reader=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1/independent-postbuild-review-1/check_selected_edges.py';source=special_reader.read_text();take=[]
for node in ast.parse(source).body:
 if isinstance(node,ast.FunctionDef)and node.name in {'exact_target_table','special'}or isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='allowed_tails'for t in node.targets):take.append(node)
exec(compile(ast.Module(body=take,type_ignores=[]),str(special_reader)+':EXACT_SPECIALIZED_READERS','exec'),globals())
a,ar=special(old,'f03_prlimit_body_result',oldimage);b,br=special(new,'f03_prlimit_body_result',image)
shape=lambda rr:[(r['offset'],r['type'],r['kind'],r['target'],r.get('literal_hex'),None if r['kind']=='EXACT_SECTION_STRING'else r['addend'])for r in rr]
assert(a['size'],a['bind'],a['type'])==(b['size'],b['bind'],b['type'])and shape(ar)==shape(br)
ab=bytearray(data(old,a));bb=bytearray(data(new,b))
for row in br:ab[row['offset']:row['offset']+8]=bytes(8);bb[row['offset']:row['offset']+8]=bytes(8)
assert ab==bb
prlimit=dict(name='f03_prlimit_body_result',exact_special_reader=ref(special_reader),all_nonrelocated_bytes_and_target_table_equal116=True,full_final_bytes_reproduced=True,targets=br)
logger_reader=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1/independent-postbuild-review-1/check_inherited_core_current112.py';text=logger_reader.read_text();segment='q=E/'+text.split('q=E/',1)[1].split('\nmetadata=[]',1)[0];img=image
exec(compile(segment,str(logger_reader)+':EXACT_FOUR_RECORD_LOGGER','exec'),globals())
logger=dict(name='arch_process_vm_rw_log_bridge',exact_reader=ref(logger_reader),records=records,bindings=bindings,other_targets=other_targets,full_current_final_bytes_and_116_equal=True)
folded=[];foldedfailures=[]
for name in ['f03_execveat_ptrace_report_v1','syscall','arch_ptrace_syscall_event','ptrace_syscall_event','f03_exec_report_signal_v1','sys_shmget','do_shmget','perf_event_alloc_map_body_result']:
 try:
  a,ab,ar,_=relocated_function(old,name);b,bb,br,rr=relocated_function(new,name,image)
  assert(a['size'],a['type'],a['bind'])==(b['size'],b['type'],b['bind'])and ab==bb and ar==br
  folded.append(dict(name=name,full_final_bytes=True,all_nonrelocated_and_symbolic_targets_equal116=True))
 except Exception as exc:foldedfailures.append(dict(name=name,error=repr(exc)))
# Bind actual snapshot source/ABI metadata to the genuine producer profile.
manifest=read(auth(profile['inputs']['source_directory_exports'][0]['manifest']));snapshots=[auth(r['snapshot'])for r in manifest['files']];assert len(snapshots)==149 and sum(p.suffix=='.rs'for p in snapshots)==138
adoption=read(auth(profile['actual_root_adoption']));assert len(adoption['canonical_rows'])==18
source_rows=[auth(row['actual'])for row in adoption['canonical_rows']]
postimages=[auth(row['postimage'])for row in profile['inputs']['postimages']]
origin={k:ref(auth(v))for k,v in profile['origin_source_materialization'].items()}
config=[auth(row['source'])for row in profile['inputs']['configuration']]
newimports={s['name']for s in new.symbols if s['shndx']==0 and s['bind']==1};oldimports={s['name']for s in old.symbols if s['shndx']==0 and s['bind']==1};import_proof=[]
for name in sorted(newimports-oldimports):
 owners=[(r['link_token'],s)for r,e in objects for s in defined(e,name)];assert len(owners)==1
 f=image.sym(name);assert(owners[0][1]['type'],owners[0][1]['size'])==(f['type'],f['size']);import_proof.append(dict(name=name,object=owners[0][0],input=owners[0][1],final=f))
assert struct.unpack_from('<16sHHIQQQIHHHHHH',image.raw)[4]==image.sym('arch_start')['value']
warnings_new=warnings(W/'evidence/00.stderr');warnings_old=warnings(Path(accept['actual_worker']['path']).parent/'00.stderr');added=list((collections.Counter(warnings_new)-collections.Counter(warnings_old)).elements());removed=list((collections.Counter(warnings_old)-collections.Counter(warnings_new)).elements())
assert collections.Counter(added)==collections.Counter(['unused imports: `CLong` and `SizeT`','unnecessary `unsafe` block','145 warnings emitted'])and removed==['143 warnings emitted']
assert warnings(W/'evidence/01.stderr')==warnings(Path(accept['actual_worker']['path']).parent/'01.stderr')
assert(W/'evidence/02.stderr').read_bytes()==(Path(accept['actual_worker']['path']).parent/'03.stderr').read_bytes()
result=dict(scope=__doc__.splitlines()[0],status='ACTUAL119_INHERITED_SPECIALIZED_AND_SOURCE_WARNING_FACTS_PENDING_INDEPENDENT_REVIEW',prlimit=prlimit,logger=logger,folded_comparisons=folded,folded_deltas=foldedfailures,source_profile=grant['profile'],source_adoption=profile['actual_root_adoption'],readonly_source_manifest=profile['inputs']['source_directory_exports'][0]['manifest'],snapshot_files=149,Rust_files=138,canonical18_all_exact=True,nonRust_postimages=len(postimages),configuration_files=len(config),actual_origin_materialization=origin,new_imports_resolved=import_proof,actual_warning_delta=dict(added=added,removed=removed,C_message_set_unchanged=True,arch_stderr_empty=True,link_stderr_equal116=True,disposition='Two new nonfatal Rust source lint sites:unused imports and unnecessaryunsafe. Original compilerwarnings preserved; no compileerrors. Independentbounded disposition required.'),final_ELF_entry_arch_start=True,artifact_acceptance=False,native_acceptance=False,wholefile_acceptance=False,runtime_authority=None)
(D/'INHERITED-SOURCE-WARNING-SUPPLEMENT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(prlimit='PASS',logger='PASS',folded=len(folded),deltas=foldedfailures,source133='PASS',new_imports=import_proof,report=ref(D/'INHERITED-SOURCE-WARNING-SUPPLEMENT.json'))))
