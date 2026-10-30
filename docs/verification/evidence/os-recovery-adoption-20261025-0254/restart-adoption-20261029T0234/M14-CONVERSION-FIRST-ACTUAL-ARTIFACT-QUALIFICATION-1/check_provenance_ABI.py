"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual source provenance and selected extern-C ABI; no compiler or runtime.
"""
from pathlib import Path
exec(compile(Path(__file__).with_name('context.py').read_text(),str(Path(__file__).with_name('context.py')),'exec'))
base=read(A/'M14-CURRENT119-ACTUAL-ARTIFACT-QUALIFICATION-1/independent-review-1/INDEPENDENT-ACTUAL-CURRENT119-ARTIFACT-ACCEPTANCE.json');bp=read(auth(base['actual_profile']))
manifest=read(auth(profile['inputs']['source_directory_exports'][0]['manifest']));bm=read(auth(bp['inputs']['source_directory_exports'][0]['manifest']));snap={x['relative']:x['snapshot']for x in manifest['files']};bsnap={x['relative']:x['snapshot']for x in bm['files']}
assert len(snap)==149 and sum(n.endswith('.rs')for n in snap)==138 and len(bsnap)==133
for r in snap.values():auth(r)
changed=[n for n in bsnap if snap[n]['sha256']!=bsnap[n]['sha256']];added=sorted(set(snap)-set(bsnap));assert sorted(changed)==['lib.rs','syscall_policy.rs'] and len(added)==16
assert profile['inputs']['external_relative_modules']==bp['inputs']['external_relative_modules']
for r in profile['inputs']['external_relative_modules']:auth(r['source'])
export=read(auth(grant['input_export_authority']));assert export['qualified_readonly_files']==[r['source']for r in profile['inputs']['configuration']]+[r['source']for r in profile['inputs']['objects']if not r['replace']]+[r['postimage']for r in profile['inputs']['postimages']]+[dict(path=r['snapshot']['path'],bytes=r['snapshot']['bytes'],sha256=r['snapshot']['sha256'])for r in manifest['files']]+[r['source']for r in profile['inputs']['external_relative_modules']]
retained=[]
for r,e in objects:
 if not r['replace']:
  src=auth(r['source']);actual=B/r['link_token'];assert actual.stat().st_size==0 and actual.stat().st_mode&0o777==0o400;retained.append(dict(link_token=r['link_token'],source=r['source'],host_mountpoint_placeholder=ref(actual),container_readonly_bind_source=r['source']['path'],container_target='/work/output/build/'+r['build_relative']))
assert len(retained)==9
assert profile['inputs']['configuration']==bp['inputs']['configuration']
configs=[]
for r in profile['inputs']['configuration']:
 p=auth(r['source']);actual=W/'output/build'/r['build_relative'];assert actual.stat().st_size==0 and actual.stat().st_mode&0o777==0o400;configs.append(dict(source=r['source'],host_mountpoint_placeholder=ref(actual),container_readonly_bind_source=r['source']['path'],container_target='/work/output/build/'+r['build_relative']))
for key in ['toolchain_mounts','toolchain_manifest','toolchain_lock_sha256','source6153']:
 assert profile['inputs'][key]==bp['inputs'][key],key
reuse=read(profile['reuse_descriptor']);assert reuse['SDK21']if 'SDK21'in reuse else reuse['retained_sdk21']=='EXACT_CURRENT119_PROFILE_AND_HISTORICAL_EXPORT_NO_RECOMPILE'
linkdep=B/'CMakeFiles/mckernel.img.dir/link.d';dep=linkdep.read_text()
for r,e in objects:assert r['link_token']in dep
assert struct.unpack_from('<16sHHIQQQIHHHHHH',image.raw)[4]==image.sym('arch_start')['value']
postimages={r['relative']:r['postimage']for r in profile['inputs']['postimages']}
for r in postimages.values():auth(r)
c=auth(postimages['kernel/syscall.c']).read_text();abi=auth(snap['abi.rs']).read_text();assert snap['abi.rs']['sha256']==bsnap['abi.rs']['sha256']
for t,x in [('CInt','i32'),('CLong','i64'),('CULong','u64'),('SizeT','usize')]:assert 'pub type '+t+' = '+x+';'in abi
scan=read(D/'CHANGE-SCAN.ACTUAL.json');wiring=read(A/'M14-CONVERSION-FIRST-COMPOSITION-1/C-WIRING-DELTAS.json');wby={r['symbol']:r for r in wiring}
assert set(scan['removed_C'])==set(scan['Rust_new'])|{'do_munmap_set_host_bridge'}
assert '#define do_munmap_set_host_bridge mprotect_set_host_vma_bridge'in c
# Exact scalar/pointer ABI under x86_64 LP64. No struct is passed by value by these leaves.
ctype={'CInt':'int','c_int':'int','CLong':'long','CULong':'unsigned long','SizeT':'size_t','*mut c_void':'void *','*mut SyscallRequest':'struct syscall_request *'}
rows=[]
for name in scan['Rust_new']:
 hits=[]
 for n in added:
  t=auth(snap[n]).read_text();m=re.search(r'(?:pub[^\n]*\s+)?(?:unsafe\s+)?extern "C" fn '+name+r'\s*\(([^)]*)\)\s*(?:->\s*([^\{]+))?',t)
  if m:hits.append((n,t,m))
 assert len(hits)==1,(name,len(hits));n,t,m=hits[0]
 params=[v.strip()for v in m[1].split(',')if v.strip()];rt=[x.split(':',1)[1].strip()for x in params];ret=(m[2]or'()').strip();expected_ret='void'if ret=='()'else ctype[ret]
 cm=re.search(r'(?:extern\s+)?(void|int|long)\s+'+name+r'\s*\(([^)]*)\)',c);assert cm,(name,'C declaration')
 cp=[x.strip()for x in cm[2].split(',')if x.strip()and x.strip()!='void'];assert len(cp)==len(rt) and cm[1]==expected_ret,(name,'arity/return')
 for ct,rust in zip(cp,rt):
  expected=ctype[rust];assert re.sub(r'\s+','',ct).startswith(re.sub(r'\s+','',expected)),(name,ct,rust)
 assert '#[no_mangle]'in t
 rows.append(dict(name=name,Rust_source=snap[n],Rust_signature=' '.join(m.group().split()),C_source=postimages['kernel/syscall.c'],C_signature=cm.group(),parameter_types=rt,return_type=ret,type_check='PASS_SELECTED_X86_64_LP64_EXTERN_C',source_borrow_scope='Synchronous caller-owned pointers/node/context; no ownership widening inferred from source or ELF'))
# Original enabled selectors are retained and added paired flags occur in actual producer argv.
a0=worker['commands'][0]['argv'];a1=worker['commands'][1]['argv']
for x in ['f03_ptrace_clone_noirq_candidate','f03_context_forward_pair_candidate','f03_wakeup_writer_pair_candidate']:assert x in a0
for x in ['-DMCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ','-DMCKERNEL_RUST_F03_CONTEXT_FORWARD_PAIR','-DMCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR']:assert x in a1
assert not any('PTRAC' in x and 'KFREE_PROFILE' in x for x in a1)
result=dict(scope=__doc__.splitlines()[0],source_manifest=profile['inputs']['source_directory_exports'][0]['manifest'],snapshot_files=149,Rust_files=138,inherited_source_files_byte_equal=131,changed_existing_sources=changed,added_sources=added,external3=profile['inputs']['external_relative_modules'],retained9=retained,configuration10=configs,SDK21_and_toolchain_reused_unchanged=True,postimages=postimages,link_dependency=ref(linkdep),raw_link_order=[r['link_token']for r,e in objects],exact_C_alias=dict(removed='do_munmap_set_host_bridge',provider='mprotect_set_host_vma_bridge',macro='#define do_munmap_set_host_bridge mprotect_set_host_vma_bridge'),selected_ABI=rows,request_abi_source=snap['abi.rs'],request_layout_unchanged_from_actual119=True,ABI29_new_codegen_proof=False,native_acceptance=False,wholefile_retirement=False)
(D/'SOURCE-ABI-PROVENANCE.ACTUAL.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(source149='PASS',retained=len(retained),config=len(configs),selected_ABI=len(rows),changed_sources=changed,added=len(added))))
