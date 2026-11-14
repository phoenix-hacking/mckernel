from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent;base=here.parent/'postimage'/'kernel';out=here/'postimage'/'kernel';root=here.parent.parent
contract=root/'M14-REMAINING23-DEFINED-CALLER-CONTRACT-1/ROOT-CONTRACTS.APPROVED.json'
assert hashlib.sha256(contract.read_bytes()).hexdigest()=='534c4df211bcf940f19191607d8d3d26d426e2f82d3bfaa7f392c41fe06df19e'
decision=json.loads(contract.read_text()); assert decision['decision']=='APPROVE_DEFINED_NAMED_CALLER_SOURCE_CONTRACTS'
ids={x['id'] for x in decision['contracts']};assert {'INTERRUPT-ARG3-5','PTRACE-WAKEUP-DEFINED-HEX'}<=ids
old=(base/'syscall.c').read_text();new=(out/'syscall.c').read_text()
original='''static void
ptrace_wakeup_log_bridge(int event, int value, int result)
{
\tif (event == PTRACE_CONTROL_LOG_WAKEUP_ENTER) {
\t\tdkprintf("ptrace_wakeup_sig,pid=%d,data=%08x\\n",
\t\t\t\tvalue, result);
\t}
}
'''
assert old.count(original)==new.count(original)==1
start=new.index('#if defined(MCKERNEL_RUST_F03_PTRACE_WAKEUP_LOG_DEFINED) && defined(MCKERNEL_RUST_F03_PTRACE_WAKEUP_LOG_PROFILE_119) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(__x86_64__)\nextern void ptrace_wakeup_log_bridge')
end=new.index('#line 24433\n',new.index(original,start))+len('#line 24433\n')
chunk=new[start:end];assert new[:start]+original+new[end:]==old
# Independent local directive model: original function begins at 24425 and
# its one ddebug invocation at 24429. No compiler is invoked.
def run(selected):
 n=24425;active=True;stack=[];ev={}
 for line in chunk.splitlines():
  s=line.strip()
  if s.startswith('#if '):stack.append(active);active=active and selected
  elif s=='#else':active=stack[-1] and not selected
  elif s=='#endif':active=stack.pop()
  elif active and s.startswith('#line '):n=int(s.split()[1]);continue
  elif active and s=='static void':ev['fallback_start']=n
  elif active and s.startswith('extern void ptrace_wakeup_log_bridge'):ev['selected_decl']=n
  if active and s.startswith('dkprintf("ptrace_wakeup_sig,'):ev['fallback_debug']=n
  n+=1
 assert not stack;ev['next_line']=n;return ev
assert run(False)=={'fallback_start':24425,'fallback_debug':24429,'next_line':24433}
assert 'selected_decl' in run(True) and run(True)['next_line']==24433 and 'fallback_debug' not in run(True)
oldp=(base/'rust/syscall_policy.rs').read_text();p=(out/'rust/syscall_policy.rs').read_text();assert p.startswith(oldp)
log=(out/'rust/syscall_ptrace_wakeup_log.rs').read_text();inter=(out/'rust/syscall_interrupt_arity3.rs').read_text()
assert (out/'rust/syscall_interrupt_arity3.rs').read_bytes()==(base/'rust/syscall_interrupt_arity3.rs').read_bytes()
assert 'ptrace_wakeup_log_bridge(event: CInt, value: CInt, result: CInt)' in log
assert 'if event == 4' in log and 'value, result as u32' in log
assert 'c"ptrace_wakeup_sig,pid=%d,data=%08x\\n"' in log
assert 'b"/src/kernel/syscall.c\\0"' in log and 'b"ptrace_wakeup_log_bridge\\0"' in log and 'line_flags: 24429' in log
assert '#[link_section = "__verbose"]' in log and 'read_volatile' in log
assert 'MaybeUninit::<X86UserContext>::uninit()' in inter and 'assume_init()' not in inter and 'zeroed()' not in inter
writes=re.findall(r'write_volatile\(addr_of_mut!\(\(\*ctx_ptr\)\.gpr\.(\w+)\), (.*?)\);',inter)
assert writes==[('rdi','(*(*thread).proc).pid as CULong'),('rsi','(*thread).tid as CULong'),('rdx','sig as CULong'),('r10','0'),('r8','0'),('r9','0')],writes
assert 'super::syscall_generic_forwarding(62, ctx_ptr)' in inter
assert inter.index('read_volatile')<inter.index('gpr.rdi')<inter.index('gpr.rsi')<inter.index('gpr.rdx')<inter.index('gpr.r10')<inter.index('gpr.r8')<inter.index('gpr.r9')<inter.index('syscall_generic_forwarding(62, ctx_ptr)')<inter.index('interrupt_syscall failed.')
assert not any(t in inter for t in ('uti_state','(*ctx_ptr).sr','(*ctx_ptr).is_gpr_valid','(*ctx_ptr).is_sr_valid','(*ctx_ptr).gpr.rax'))
cm=(out/'CMakeLists.txt').read_text()
condition='MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12" AND NOT ENABLE_UBSAN AND\n';assert cm.count(condition)==2
assert cm.count('CMAKE_CURRENT_SOURCE_DIR STREQUAL "/src/kernel"')==2
for f in ['f03_interrupt_arity3_defined_candidate','f03_interrupt_origin_profile_119','f03_interrupt_origin_dispatch','f03_ptrace_wakeup_log_defined_u32_candidate','f03_ptrace_wakeup_log_origin_profile_119','MCKERNEL_RUST_F03_INTERRUPT_ARITY3_DEFINED','MCKERNEL_RUST_F03_INTERRUPT_ORIGIN_PROFILE_119','MCKERNEL_RUST_F03_PTRACE_WAKEUP_LOG_DEFINED','MCKERNEL_RUST_F03_PTRACE_WAKEUP_LOG_PROFILE_119']:
 assert cm.count(f)==1,f
for f in ['syscall_terminate_whole.rs','syscall_terminate_mcexec_whole.rs','syscall_terminate_host_whole.rs','syscall_ptrace_detach_kfree.rs','syscall_ptrace_detach_kill.rs','syscall_interrupt_arity3.rs']:
 assert (out/'rust'/f).read_bytes()==(base/'rust'/f).read_bytes()
# Defined-format expectation from the approved contract; not a C UB oracle.
vec=[]
for v in (-2147483648,-1,0,1,2147483647):
 vec.append({'event':4,'value':-3,'result':v,'expected':'ptrace_wakeup_sig,pid=-3,data='+format(v&0xffffffff,'08x')+'\n'})
assert vec[1]['expected']=='ptrace_wakeup_sig,pid=-3,data=ffffffff\n'
assert all(v['event']==4 for v in vec)
# Reference x86 field map was bound by Queue C source check; no actual provider execution.
x86=Path('/home/holden/mckernel/kernel/rust/x86_cpu_helpers.rs').read_text()
for i,f in enumerate(['rdi','rsi','rdx','r10','r8','r9']):assert str(i)+' => read_volatile(&(*uctx).gpr.'+f+')' in x86
def info(x):
 b=x.read_bytes();return {'path':str(x),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'APPROVED_CONTRACT_SOURCE_COMPOSITION_ONLY','checks':['approved exact contract hash','logger selected/OFF model and original line restoration','original C logger restored by reversal','u32 negative and edge format examples against approved definition','six raw field writes, pid/tid/sig conversion and order; no aggregate initialization','existing x86 accessor mapping','same source-bound C and Rust selector condition','parent Rust prefix and retained six module identities'], 'logger_model':{'off':run(False),'on':run(True)},'defined_format_vectors':vec,'patch':info(here/'DEFINED-CALLERS.PRIVATE-NOT-APPLIED.patch'),'contract':info(contract),'outputs':[info(out/'syscall.c'),info(out/'rust/syscall_policy.rs'),info(out/'CMakeLists.txt'),info(out/'rust/syscall_ptrace_wakeup_log.rs')], 'limitations':'Pure source/model checks; no preprocessor, actual varargs, compiler/link/native/389 ABI/metadata acceptance or hold clearance.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'checks':r['checks'],'patch':r['patch']},indent=2))
