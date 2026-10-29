"""Functional OS forwarding/ABI/source identity checks; no security testing.
No actual clear_host_pte, VM, compiler, HOST payload, guard or native invocation.
"""
from pathlib import Path
import json,re,hashlib
D=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel')
pre=(D/'preimage/kernel/syscall.c').read_text();post=(D/'postimage/kernel/syscall.c').read_text();rp=(D/'preimage/kernel/rust/syscall_policy.rs').read_text();rq=(D/'postimage/kernel/rust/syscall_policy.rs').read_text();leaf=(D/'postimage/kernel/rust/syscall_munmap_clear_host_forward.rs').read_text();abi=(ROOT/'kernel/rust/abi.rs').read_text()
start=pre.index('static long\ndo_munmap_clear_host_bridge(');end=pre.index('\nstatic int\ndo_munmap_set_host_bridge',start);first=pre.count('\n',0,start);stop=pre.count('\n',0,end);a=pre.splitlines(True);b=post.splitlines(True);assert len(a)==len(b)and a[:first]==b[:first]and a[stop:]==b[stop:]
token=lambda s:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[^\s]',s);assert token(''.join(a[first:stop]))==token(b[first+3]);assert b[first].strip()=='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)';assert b[first+1].strip()=='extern long do_munmap_clear_host_bridge(unsigned long addr, size_t len, int holding_lock);'
assert 'typedef long (*do_munmap_clear_host_fn_t)(unsigned long addr, size_t len,'in pre and '.clear_host = do_munmap_clear_host_bridge,'in pre
assert 'unsafe extern "C" fn(CULong, SizeT, CInt) -> CLong' in leaf and 'const _: ClearHostFn = clear_host_pte;'in leaf and 'const _: ClearHostFn = do_munmap_clear_host_bridge;'in leaf
for alias in ['pub type CInt = i32;','pub type CLong = i64;','pub type CULong = u64;','pub type SizeT = usize;']:assert alias in abi
assert 'use super::f03_clear_host_pte_entry_v1::clear_host_pte;'in leaf and leaf.count('clear_host_pte(')==1 and 'unsafe { clear_host_pte(addr, len, holding_lock) }'in leaf
assert rq.startswith(rp);assert rq[len(rp):].count('mod syscall_munmap_clear_host_forward;')==1
# Preserve every inherited Rust location-sensitive macro site, not a subset.
def sites(text,name):return[(i,m.start()+1,line)for i,line in enumerate(text.splitlines(),1)for m in re.finditer(r'\b'+name+r'!\s*\(',line)]
for macro in ['line','file','column']:assert sites(rp,macro)==sites(rq,macro)
assert len(sites(rq,'line'))==53
assert not sites(leaf,'line')and 'Ddebug'not in leaf and '__verbose'not in leaf
origins=lambda s:[(i,line)for i,line in enumerate(s.splitlines(True),1)if re.match(r'^\s*#\s*(?:line\b|\d)',line)];assert origins(pre)==origins(post)
cm=(D/'preimage/kernel/CMakeLists.txt').read_text();cn=(D/'postimage/kernel/CMakeLists.txt').read_text();dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_munmap_clear_host_forward.rs"\n';assert cn.count(dep)==1 and cn.replace(dep,'',1)==cm
assert 'list(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")'in cm and 'MCKERNEL_RUST_F03_LEAF_CALLBACKS'in cm
assert '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]'in rq[len(rp):]
# Source-derived forwarding fixture. The provider is a stub, not a real VM call;
# verify raw scalar bit identity, one call and unchanged signed return values.
c_pattern=re.search(r'return\s+clear_host_pte\(([^)]*)\);',''.join(a[first:stop]));r_pattern=re.search(r'unsafe\s*\{\s*clear_host_pte\(([^)]*)\)\s*\}',leaf);assert c_pattern and r_pattern;c_args=[x.strip()for x in c_pattern.group(1).split(',')];r_args=[x.strip()for x in r_pattern.group(1).split(',')];assert c_args==r_args==['addr','len','holding_lock']
inputs=[(0,0,0),(1,1,1),((1<<64)-1,(1<<64)-1,-1),(0xffff800000001000,4096,2),(0,4096,-(1<<31)),(4096,0,(1<<31)-1)]
returns=[-(1<<63),-22,-14,-1,0,1,(1<<63)-1];cases=0
for values in inputs:
 env=dict(zip(['addr','len','holding_lock'],values))
 for result in returns:
  traces=[]
  def provider(*args):traces.append(args);return result
  c_result=provider(*(env[k]for k in c_args));r_result=provider(*(env[k]for k in r_args));assert traces==[values,values]and c_result==r_result==result;cases+=1
selection=json.loads((D/'SELECTION-EVIDENCE.json').read_text());assert len(selection['allocated_generic_C_function_names'])==42 and selection['allocated_generic_C_function_names'].count('do_munmap_clear_host_bridge')==1
checks=['actual42list contains selected callback; no duplicate existing port','exact existing int/long/ulong/size_t ABI aliases plus both function-pointer assertions','selected C extern and OFF fallback tokens exact; no changed VM/callee/parentbody/binding data','one direct existing Rust provider call with same3scalarargs/signedreturn,42stub forwardingcases','entire parent Rust byteprefix and all53line!/file!/column! identities preserved byEOFmodule','Cnewline/#line positions unchanged, no descriptor/oracle rows added/removed, original389sourceidentity preserved','one module/dependency and existing paired leafcallback+x86 selection, no new profile']
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_PRIVATE_SOURCE_FORWARDING_CONTRACT',checks=checks,source_fixture_cases=cases,actual_VM_provider_calls=0,actual_ABI_compile=False,actual_linked389=False,compiler_HOST_native_calls=0),indent=2)+'\n');print('PASS',len(checks),'source groups;',cases,'pure forwarding cases')
