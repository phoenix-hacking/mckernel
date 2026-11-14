"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source/header/unsafe-prefix review; no compiler or callback execution.
"""
from pathlib import Path
import ast,hashlib,json,re
D=Path(__file__).resolve().parent;P=D.parent;ROOT=Path('/home/holden/mckernel')

def read(p):return json.loads(p.read_bytes())
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(row):assert ref(Path(row['path']))==row;return Path(row['path'])
def plain(text):return re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
def function(text,name):
 hit=re.search(r'\bfn\s+'+name+r'\s*\(',text);assert hit;start=hit.start();opening=text.index('{',start);depth=0
 for i in range(opening,len(text)):
  if text[i]=='{':depth+=1
  if text[i]=='}':
   depth-=1
   if depth==0:return text[start:i+1]
 raise AssertionError(name)
ready=read(P/'SOURCE-READY.json');assert ref(P/'SOURCE-READY.json')['sha256'].startswith('a2613fa0')
for row in ready['files'].values():auth(row)
leaf=auth(ready['leaf']).read_text();assert ready['leaf']['sha256']=='11a6131f8f8e826912602bf89fdd32bad7675d184f4e43c16b6375f54d17b881'
pre=(P/'preimage/kernel/syscall.c').read_text();post=(P/'postimage/kernel/syscall.c').read_text();rp=(P/'preimage/kernel/rust/syscall_policy.rs').read_text();rq=(P/'postimage/kernel/rust/syscall_policy.rs').read_text();abi=(ROOT/'kernel/rust/abi.rs').read_text();helpers=(ROOT/'kernel/rust/x86_cpu_helpers.rs').read_text();header=(ROOT/'arch/x86_64/kernel/include/ihk/context.h').read_text();regs=(ROOT/'arch/x86_64/kernel/include/registers.h').read_text()
start=pre.index('static int set_host_vma(uintptr_t addr, size_t len, int prot, int holding_memory_range_lock)');end=pre.index('return set_host_vma_body_result(',start);prefix=plain(pre[start:end]);assert re.findall(r'\b(get_this_cpu_local_var|ihk_mc_syscall_set_arg[012])\s*\(',prefix)==['get_this_cpu_local_var','ihk_mc_syscall_set_arg0','ihk_mc_syscall_set_arg1','ihk_mc_syscall_set_arg2']
writer=plain(function(helpers,'x86_syscall_write'))
for i,field in [(0,'rdi'),(1,'rsi'),(2,'rdx')]:
 name='ihk_mc_syscall_set_arg'+str(i);fn=plain(function(helpers,name));assert 'uctx: *mut X86UserContext, value: CULong'in fn and f'x86_syscall_write(uctx, {i}, value)'in fn;assert f'{i} => write_volatile(&mut (*uctx).gpr.{field}, value),'in writer;assert f'void {name}(ihk_mc_user_context_t *uc, unsigned long value);'in header
shapes={}
for name,allowed in [('X86BasicRegs',{'CULong'}),('X86Sregs',{'CULong'}),('X86UserContext',{'X86Sregs','X86BasicRegs','u8'})]:
 body=plain(re.search(r'#\[repr\(C\)\]\npub struct '+name+r' \{(.*?)\n\}',abi,re.S).group(1));fields=re.findall(r'pub\s+(\w+)\s*:\s*([^,]+),',body);assert fields and all(t.strip()in allowed for _,t in fields);assert len(re.findall(r'\bpub\b',body))==len(fields);shapes[name]=fields
assert[len(shapes[k])for k in ['X86BasicRegs','X86Sregs','X86UserContext']]==[21,6,10]
assert 'pub type CULong = u64;'in abi and 'pub type CInt = i32;'in abi and 'pub type SizeT = usize;'in abi
for assertion in ['assert_eq_usize(size_of::<X86UserContext>(), 224);','assert_eq_usize(offset_of!(X86UserContext, gpr), 56);']:assert assertion in abi
assert 'typedef struct x86_user_context ihk_mc_user_context_t;'in header and 'struct x86_basic_regs'in regs and 'struct x86_sregs'in regs
# Independently constrain exact new scratch lifetime/callshape, not real behavior.
def prefix_valid(candidate):
 body=plain(function(candidate,'mprotect_set_host_vma_bridge'))
 assert 'let mut ctx = MaybeUninit::<X86UserContext>::zeroed();'in body
 assert 'let _thread = unsafe { (*get_this_cpu_local_var()).current };'in body
 calls=re.findall(r'\b(get_this_cpu_local_var|ihk_mc_syscall_set_arg[012]|set_host_vma_body_result)\s*\(',body);assert calls==['get_this_cpu_local_var','ihk_mc_syscall_set_arg0','ihk_mc_syscall_set_arg1','ihk_mc_syscall_set_arg2','set_host_vma_body_result']
 for text in ['ihk_mc_syscall_set_arg0(ctx.as_mut_ptr(), start);','ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);','ihk_mc_syscall_set_arg2(ctx.as_mut_ptr(), prot as CULong);','set_host_vma_body_result(start, len, prot, holding_lock)']:assert text in body
 assert len(re.findall(r'\bctx\b',body))==4 and body.count('ctx.as_mut_ptr()')==3
 assert ' as u32'not in body and 'set_host_vma('not in body
 return True
assert prefix_valid(leaf)
for changed in [leaf.replace('ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);',''),leaf.replace('prot as CULong','prot as u32 as CULong'),leaf.replace('ihk_mc_syscall_set_arg0(ctx.as_mut_ptr(), start);','ihk_mc_syscall_set_arg2(ctx.as_mut_ptr(), prot as CULong);')]:
 try:prefix_valid(changed)
 except AssertionError:pass
 else:raise AssertionError('mutated prefix accepted')
for text in ['type SetArgFn = unsafe extern "C" fn(*mut X86UserContext, CULong);','type HostVmaFn = unsafe extern "C" fn(CULong, SizeT, CInt, CInt) -> CInt;','const _: HostVmaFn = set_host_vma_body_result;','const _: HostVmaFn = mprotect_set_host_vma_bridge;']:assert text in leaf
callback=pre.index('static int mprotect_set_host_vma_bridge(');stop=pre.index('\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',callback);first=pre.count('\n',0,callback);last=pre.count('\n',0,stop);a=pre.splitlines(True);b=post.splitlines(True);assert len(a)==len(b)and a[:first]==b[:first]and a[last:]==b[last:]
tokens=lambda t:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[^\s]',t);assert tokens(''.join(a[first:last]))==tokens(b[first+3]);assert b[first].strip()=='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)'
assert rq.startswith(rp);tail=rq[len(rp):];assert tail.count('mod syscall_mprotect_host_vma;')==1 and '#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]'in tail
sites=lambda text,macro:[(i,m.start()+1,line)for i,line in enumerate(text.splitlines(),1)for m in re.finditer(r'\b'+macro+r'!\s*\(',line)]
for macro in ['line','file','column']:assert sites(rp,macro)==sites(rq,macro)
assert len(sites(rq,'line'))==len(sites(rq,'file'))==53
cm=(P/'preimage/kernel/CMakeLists.txt').read_text();cn=(P/'postimage/kernel/CMakeLists.txt').read_text();dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"\n';assert cn.count(dep)==1 and cn.replace(dep,'',1)==cm
conversions=[dict(prot=v,expected_unsigned64=v%(1<<64),wrong_unsigned32=v%(1<<32))for v in [-(1<<31),-1,0,1,(1<<31)-1]];assert conversions[0]['expected_unsigned64']!=conversions[0]['wrong_unsigned32']and conversions[1]['expected_unsigned64']==(1<<64)-1
result=dict(scope=__doc__.splitlines()[0],status='PASS_SOURCE_FULL_REACHABLE_MPROTECT_PREFIX_UNSAFE_AND_ABI_CONTRACT',source_ready=ref(P/'SOURCE-READY.json'),leaf=ready['leaf'],source_headers={str(p.relative_to(ROOT)):ref(p)for p in [ROOT/'kernel/rust/abi.rs',ROOT/'kernel/rust/x86_cpu_helpers.rs',ROOT/'arch/x86_64/kernel/include/ihk/context.h',ROOT/'arch/x86_64/kernel/include/registers.h']},zero_valid_nested_shapes=shapes,call_order=['currentCPU_currentread','volatile_arg0_rdi','volatile_arg1_rsi','volatile_arg2_rdx','qualified_Rust_body'],scratch_size=224,scratch_gpr_offset=56,scratch_only_three_setter_pointer_uses=True,scratch_does_not_escape_or_reach_body=True,exact_int_to_unsigned64_conversion=conversions,negative_memory_only_mutations_rejected=3,original_C_helper_and_other_users_unchanged=True,no_C_set_host_vma_dependency_added=True,full_original_Rust_policy_prefix=True,all53line_and53file_origins_unchanged=True,actual_compiler_ELF_HOST_native_guard_proc_stage_cleanup_billing_calls=0,runtime_authority=None)
(D/'CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],report=ref(D/'CHECKS.json'))))
