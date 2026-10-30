from pathlib import Path
import subprocess,re
before=Path('preimage/kernel/syscall.c').read_text(); after=Path('postimage/kernel/syscall.c').read_text()
anchor='#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n#line 4490'
wakeup='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\nextern void ptrace_detach_wakeup_bridge'
start='static long\nptrace_detach_do_kill_bridge'
def slice_source(s):
 a=s.index(anchor); b=s.index('#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nstatic void\nptrace_detach_release_thread_bridge',a)
 t=s[a:b]
 assert t.count(start)==1 and t.count(wakeup)==1
 t=t.replace(start,'enum { kill_line = __LINE__ }; static long\nptrace_detach_do_kill_bridge')
 t=t.replace(wakeup,'enum { wake_line = __LINE__ };\n'+wakeup)
 return t
for name,defines in [('dispatch', ['MCKERNEL_RUST_SYSCALL_OFFLOAD','MCKERNEL_RUST_SYSCALL_POLICY_HELPERS','MCKERNEL_RUST_F03_DISPATCH_CONTEXT','MCKERNEL_RUST_F03_LEAF_CALLBACKS']),('fallback',[]),('helper_without_dispatch',['MCKERNEL_RUST_SYSCALL_POLICY_HELPERS','MCKERNEL_RUST_F03_LEAF_CALLBACKS'])]:
 def run(src,selected):
  args=['cc','-E','-P','-x','c','-']+['-D'+x for x in defines]+(['-DMCKERNEL_RUST_F03_PTRACE_DETACH_KILL_EXPERIMENTAL'] if selected else [])
  return subprocess.run(args,input=slice_source(src),text=True,capture_output=True,check=True).stdout
 def values(out):return {k:int(v) for k,v in re.findall(r'(kill_line|wake_line)\s*=\s*(\d+)',out)}
 original=run(before,False); off=run(after,False); on=run(after,True)
 assert values(original)==values(off),(name,values(original),values(off))
 assert values(original)['wake_line']==values(on)['wake_line'],(name,values(original),values(on))
 is_selected=('MCKERNEL_RUST_SYSCALL_POLICY_HELPERS' in defines and 'MCKERNEL_RUST_F03_LEAF_CALLBACKS' in defines)
 assert ('extern long ptrace_detach_do_kill_bridge' in on)==is_selected
 if not is_selected: assert values(on)==values(original)
 print(name,'off',values(off),'on',values(on),'selected',is_selected)
cm=Path('postimage/kernel/CMakeLists.txt').read_text(); rust=Path('postimage/kernel/rust/syscall_policy.rs').read_text(); body=Path('postimage/kernel/rust/syscall_ptrace_detach_kill.rs').read_bytes()
assert cm.count('if (MCKERNEL_F03_PTRACE_DETACH_KILL_EXPERIMENTAL)')==2
assert cm.count('f03_ptrace_detach_kill_candidate')==1 and cm.count('MCKERNEL_RUST_F03_PTRACE_DETACH_KILL_EXPERIMENTAL')==1
assert '#[cfg(all(f03_leaf_callbacks_candidate, f03_ptrace_detach_kill_candidate, target_arch = "x86_64"))]' in rust
assert b'super::f06_ptrace_report_signal_kill(' in body
print('PASS isolated CPP fallback/selection/origin and paired source assertions; not actual TU, ABI or link')
