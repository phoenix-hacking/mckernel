"""Functional OS declared-ABI/side-effect SOURCE checks only; no security testing.
These are source-contract/mutation checks, never mirrors claimed as behavior proof.
"""
from pathlib import Path
import json,re
D=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel')
pre=(D/'preimage/kernel/syscall.c').read_text();post=(D/'postimage/kernel/syscall.c').read_text();rp=(D/'preimage/kernel/rust/syscall_policy.rs').read_text();rq=(D/'postimage/kernel/rust/syscall_policy.rs').read_text();leaf=(D/'postimage/kernel/rust/syscall_mprotect_host_vma.rs').read_text();abi=(ROOT/'kernel/rust/abi.rs').read_text();helpers=(ROOT/'kernel/rust/x86_cpu_helpers.rs').read_text();header=(ROOT/'arch/x86_64/kernel/include/ihk/context.h').read_text()
def segment(source,name):
 # Bounded extraction of one known source function, not a general Rust parser.
 hits=list(re.finditer(r'\bfn\s+'+name+r'\s*\(',source));assert len(hits)==1,name;start=hits[0].start();opening=source.index('{',start);depth=0
 for i in range(opening,len(source)):
  if source[i]=='{':depth+=1
  if source[i]=='}':
   depth-=1
   if depth==0:return source[start:i+1]
 raise AssertionError(name)
def no_comments(s):return re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)
# Source-selected chain: exact C wrapper forwards to set_host_vma; all reachable
# C prefix effects occur before its FIRST Rustbody return. Unreachable tail stays C.
helper_start=pre.index('static int set_host_vma(uintptr_t addr, size_t len, int prot, int holding_memory_range_lock)');ret=pre.index('return set_host_vma_body_result(',helper_start);c_prefix=no_comments(pre[helper_start:ret]);assert re.findall(r'\b(get_this_cpu_local_var|ihk_mc_syscall_set_arg[012])\s*\(',c_prefix)==['get_this_cpu_local_var','ihk_mc_syscall_set_arg0','ihk_mc_syscall_set_arg1','ihk_mc_syscall_set_arg2']
assert 'return set_host_vma_body_result(addr, len, prot,\n\t\t\tholding_memory_range_lock);'in pre[ret:ret+140]
# Actual existing helper source, not stubs: route fixed selectors to volatile
# writes and preserve exact C unsigned-long prototype for all3setter functions.
writer=segment(helpers,'x86_syscall_write');routes={}
for index,field in [(0,'rdi'),(1,'rsi'),(2,'rdx')]:
 name='ihk_mc_syscall_set_arg'+str(index);body=segment(helpers,name);assert 'uctx: *mut X86UserContext, value: CULong'in body and f'x86_syscall_write(uctx, {index}, value)'in body
 assert f'void {name}(ihk_mc_user_context_t *uc, unsigned long value);'in header
 assert f'{index} => write_volatile(&mut (*uctx).gpr.{field}, value),'in writer;routes[name]=dict(selector=index,volatile_field='gpr.'+field,C_value_type='unsigned long',Rust_value_type='CULong')
# Exact declared nested shape proves scratchzero validity (no enum/bool/reference,
# pointer or uninitialized field assumption) and reuses existing header/layout.
shapes={}
for struct,allowed in [('X86BasicRegs',{'CULong'}),('X86Sregs',{'CULong'}),('X86UserContext',{'X86BasicRegs','X86Sregs','u8'})]:
 body=re.search(r'#\[repr\(C\)\]\npub struct '+struct+r' \{(.*?)\n\}',abi,re.S).group(1);fields=re.findall(r'pub (\w+): ([A-Za-z_0-9]+),',body);assert fields and all(t in allowed for _,t in fields);shapes[struct]=fields
assert len(shapes['X86BasicRegs'])==21 and len(shapes['X86Sregs'])==6 and len(shapes['X86UserContext'])==10
for assertion in ['assert_eq_usize(size_of::<X86UserContext>(), 224);','assert_eq_usize(offset_of!(X86UserContext, gpr), 56);']:assert assertion in abi
assert 'typedef struct x86_user_context ihk_mc_user_context_t;'in header
for alias in ['pub type CInt = i32;','pub type CULong = u64;','pub type SizeT = usize;']:assert alias in abi
# Validate new function source has all original effects in exact order and only
# direct, type-proven conversions. Negative mutations are memory-only fixtures.
def validate_prefix(candidate):
 body=no_comments(segment(candidate,'mprotect_set_host_vma_bridge'))
 assert 'MaybeUninit::<X86UserContext>::zeroed()'in body and '(*get_this_cpu_local_var()).current'in body
 calls=re.findall(r'\b(get_this_cpu_local_var|ihk_mc_syscall_set_arg[012]|set_host_vma_body_result)\s*\(',body)
 assert calls==['get_this_cpu_local_var','ihk_mc_syscall_set_arg0','ihk_mc_syscall_set_arg1','ihk_mc_syscall_set_arg2','set_host_vma_body_result']
 for line in ['ihk_mc_syscall_set_arg0(ctx.as_mut_ptr(), start);','ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);','ihk_mc_syscall_set_arg2(ctx.as_mut_ptr(), prot as CULong);','set_host_vma_body_result(start, len, prot, holding_lock)']:assert line in body
 assert 'unsafe extern "C" fn mprotect_set_host_vma_bridge('in candidate and ') -> CInt'in body
 return calls
calls=validate_prefix(leaf)
mutations=[leaf.replace('ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);',''),leaf.replace('ihk_mc_syscall_set_arg0(ctx.as_mut_ptr(), start);','ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);').replace('ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);\n        ihk_mc_syscall_set_arg2','ihk_mc_syscall_set_arg0(ctx.as_mut_ptr(), start);\n        ihk_mc_syscall_set_arg2'),leaf.replace('prot as CULong','prot as u32 as CULong')]
for candidate in mutations:
 try:validate_prefix(candidate)
 except AssertionError:pass
 else:raise AssertionError('changed prefix/cast accepted')
# Declared C int→unsignedlong conversion is modulo2^64, not narrowing throughu32.
conversion=[dict(prot=p,C_unsigned_long=p%(1<<64),narrowed_u32=p%(1<<32))for p in [-(1<<31),-1,0,1,(1<<31)-1]];assert conversion[0]['C_unsigned_long']!=conversion[0]['narrowed_u32']and conversion[1]['C_unsigned_long']==(1<<64)-1
# Prefix leaves whole qualified Rustbody and other C helper/users unchanged.
start=pre.index('static int mprotect_set_host_vma_bridge(');end=pre.index('\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',start);first=pre.count('\n',0,start);stop=pre.count('\n',0,end);a=pre.splitlines(True);b=post.splitlines(True);assert len(a)==len(b)and a[:first]==b[:first]and a[stop:]==b[stop:]
token=lambda s:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[^\s]',s);assert token(''.join(a[first:stop]))==token(b[first+3]);assert b[first].strip()=='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)'
assert rq.startswith(rp);tail=rq[len(rp):];assert '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]'in tail and tail.count('mod syscall_mprotect_host_vma;')==1
sites=lambda s,m:[(i,x.start()+1,line)for i,line in enumerate(s.splitlines(),1)for x in re.finditer(r'\b'+m+r'!\s*\(',line)]
for macro in ['line','file','column']:assert sites(rp,macro)==sites(rq,macro)
assert len(sites(rq,'line'))==53
origins=lambda s:[(i,line)for i,line in enumerate(s.splitlines(True),1)if re.match(r'^\s*#\s*(?:line\b|\d)',line)];assert origins(pre)==origins(post)
cm=(D/'preimage/kernel/CMakeLists.txt').read_text();cn=(D/'postimage/kernel/CMakeLists.txt').read_text();dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"\n';assert cn.count(dep)==1 and cn.replace(dep,'',1)==cm
assert 'list(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")'in cm and 'MCKERNEL_RUST_F03_LEAF_CALLBACKS'in cm
checks=['actualCreachableprefix and existinghelpers prove CPUread→3volatilewrites→qualifiedRustbody order','header/ABI/functionpointer declarations plus224B/gpr56assertions reused, nestedallinteger scratchzero valid','three memory-only omission/reordering/narrowing mutations refused, declared signedconversion cases retained','originalcallbackABI/4bodyargs/return/provider unchanged, no Cset_host_vma forwardingdependency','OFF Ctokens and all Cnewline/#line positions unchanged; entireRustprefix/all53location macros unchanged','oneEOFmodule/CMake dep usingexistingpairedselector, no descriptor/oracle edit, no realVM behavior claim']
(D/'PREFIX-SOURCE-CONTRACT.json').write_text(json.dumps(dict(status='SOURCE_CONTRACT_ONLY',observed_declared_call_order=calls,actual_existing_helper_routes=routes,zero_valid_nested_struct_shapes=shapes,defined_C_conversion=conversion,scratch_pointer_escape=False,existing_provider='syscall_policy::set_host_vma_body_result'),indent=2)+'\n')
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_SOURCE_DECLARED_PREFIX_ABI_AND_ORDER_ONLY',checks=checks,mutation_negative_cases=3,actual_C_or_Rust_execution=False,compiler_HOST_native_calls=0),indent=2)+'\n');print('PASS',len(checks),'declared source groups;3negative mutations')
