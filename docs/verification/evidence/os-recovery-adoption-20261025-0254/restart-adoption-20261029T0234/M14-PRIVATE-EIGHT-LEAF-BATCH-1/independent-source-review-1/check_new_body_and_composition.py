"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One new forwarding body and exact composition only; accepted7body proofs reused.
"""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,re
D=Path(__file__).resolve().parent;P=D.parent;A=P.parent

def read(p):return json.loads(p.read_bytes())
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(row):assert ref(Path(row['path']))==row;return Path(row['path'])
ready=read(P/'SOURCE-READY.json');assert ref(P/'SOURCE-READY.json')['sha256'].startswith('3bb9ddef');auth(ready['patch']);prior=read(auth(ready['seven_leaf_independent_source_review']));assert prior['decision']=='PASS_SOURCE_EXACT_LINE_PRESERVING_SEVEN_LEAF_COMPOSITION'and prior['independent']and not prior['implementation_ownership']
B=Path(ready['seven_leaf_ready']['path']).parent;auth(ready['seven_leaf_ready']);newready=read(auth(ready['new_body_ready']));leafpath=auth(newready['leaf']);leaf=leafpath.read_text();assert newready['leaf']['sha256']=='8c0f771b28c76551f387b4936064b05ef8c646d22045ad296b98cd4abd7c6ec1'
m=read(P/'FILEMAP.SOURCE-ONLY.json');bm=read(B/'FILEMAP.SOURCE-ONLY.json');rows={r['proposed_path']:r for r in m['files']};oldrows={r['proposed_path']:r for r in bm['files']};assert len(rows)==12
for row in rows.values():auth(row['postimage'])
for name,row in oldrows.items():
 if name not in ['kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt']:assert Path(row['postimage']['path']).read_bytes()==Path(rows[name]['postimage']['path']).read_bytes()
assert(P/'postimage/kernel/rust/syscall_munmap_clear_host_forward.rs').read_bytes()==leafpath.read_bytes()
old=(B/'postimage/kernel/rust/syscall_policy.rs').read_text();post=(P/'postimage/kernel/rust/syscall_policy.rs').read_text();pre=(P/'preimage/kernel/rust/syscall_policy.rs').read_text();assert post.startswith(old)and old.startswith(pre)
tail=post[len(old):];expected='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]\n#[path = "syscall_munmap_clear_host_forward.rs"]\nmod syscall_munmap_clear_host_forward;\n';assert tail==expected
for signature in ['unsafe extern "C" fn(CULong, SizeT, CInt) -> CLong','const _: ClearHostFn = clear_host_pte;','const _: ClearHostFn = do_munmap_clear_host_bridge;','use super::f03_clear_host_pte_entry_v1::clear_host_pte;','unsafe { clear_host_pte(addr, len, holding_lock) }']:assert signature in leaf
assert leaf.count('clear_host_pte(')==1 and ' as 'not in leaf and 'Ddebug'not in leaf and '__verbose'not in leaf
assert 'pub unsafe extern "C" fn clear_host_pte(\n        addr: CULong, len: SizeT, holding_lock: CInt,\n    ) -> CLong'in pre
abi=(A/'CURRENT119-EXACT-RUST-SOURCE-EXPORT-1/rust-subtree/abi.rs').read_text()
for alias in ['pub type CInt = i32;','pub type CLong = i64;','pub type CULong = u64;','pub type SizeT = usize;']:assert alias in abi
oc=(B/'postimage/kernel/syscall.c').read_text();nc=(P/'postimage/kernel/syscall.c').read_text();start=oc.index('static long\ndo_munmap_clear_host_bridge(');end=oc.index('\nstatic int\ndo_munmap_set_host_bridge',start);first=oc.count('\n',0,start);stop=oc.count('\n',0,end);a=oc.splitlines(True);b=nc.splitlines(True);assert len(a)==len(b)and a[:first]==b[:first]and a[stop:]==b[stop:]
tokens=lambda text:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[^\s]',text);assert tokens(''.join(a[first:stop]))==tokens(b[first+3]);assert b[first].strip()=='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)';assert b[first+1].strip()=='extern long do_munmap_clear_host_bridge(unsigned long addr, size_t len, int holding_lock);';assert b[first+2].strip()=='#else'and b[first+4].strip()=='#endif'
assert re.search(r'return\s+clear_host_pte\(addr, len, holding_lock\);',''.join(a[first:stop]))
# No casts/extraarguments/boolean normalization can pass the exact forwarding shape.
for wrong in ['clear_host_pte(addr, holding_lock, len)','clear_host_pte(addr, len, holding_lock != 0)','clear_host_pte(addr as u32, len, holding_lock)']:assert wrong not in leaf
sites=lambda text,macro:[(i,match.start()+1,line)for i,line in enumerate(text.splitlines(),1)for match in re.finditer(r'\b'+macro+r'!\s*\(',line)]
for macro in ['line','file','column']:assert sites(pre,macro)==sites(old,macro)==sites(post,macro)
assert len(sites(post,'line'))==len(sites(post,'file'))==53
cm=(P/'postimage/kernel/CMakeLists.txt').read_text();oldcm=(B/'postimage/kernel/CMakeLists.txt').read_text();dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_munmap_clear_host_forward.rs"\n';assert cm.count(dep)==1 and cm.replace(dep,'',1)==oldcm
assert 'list(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")'in cm and 'MCKERNEL_RUST_F03_LEAF_CALLBACKS'in cm
directives=lambda text:[(i,line)for i,line in enumerate(text.splitlines(),1)if re.match(r'^\s*#\s*(?:line\b|\d)',line)];assert directives(oc)==directives(nc)
# New leaf has no descriptor; all seven existing descriptor leaves remain exact,
# and every inheritedmacroorigin is exact. Reuse prior complete389sourceprojection.
assert ready['reused_leaf_count']==8 and prior['source_blockers']==[]
result=dict(scope=__doc__.splitlines()[0],status='PASS_NEW_FORWARDING_SOURCE_AND_EXACT_EIGHT_LEAF_COMPOSITION',source_ready=ref(P/'SOURCE-READY.json'),patch=ready['patch'],new_body_ready=ready['new_body_ready'],new_leaf=newready['leaf'],reused_seven_source_review=ready['seven_leaf_independent_source_review'],all_prior_seven_leaf_and_lib_bytes_unchanged=True,new_body_effect='One exact existingqualifiedRust clear_host_pte scalarcall/result, no extraVM/host/lock/endpoint effects',ABI_source='long(ulong,size_t,int) LP64 matches CLong(CULong,SizeT,CInt); both compile-timefunctionpointerchecks present, no actualnewcompile claimed',C_OFF_tokens_and_selected_extern_exact=True,only_new_C_region_changed=True,only_new_Rust_EOF_module=True,one_new_CMake_dependency=True,all53line_and53file_sites_exact=True,source389_projection_reused_unchanged=True,undefined_variadic_and_other_domain_holds_preserved=True,source_forwarding42fixture_reused_not_rerun=True,actual_compiler_preprocessor_ELF_HOST_native_guard_proc_stage_cleanup_billing_calls=0,runtime_authority=None)
(D/'CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],report=ref(D/'CHECKS.json'))))
