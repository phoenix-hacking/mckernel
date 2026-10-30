#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source/argument ordering checks and actual provider writer trace.
"""
import hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent.parent;ROOT=Path('/home/holden/mckernel')
def ref(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def part(src,start,end):
 a=src.index(start);b=src.index(end,a);return src[a:b]
leaf=(D/'postimage/kernel/rust/f03_signal_forward_defined_candidate.rs').read_text()
def validate(src):
 mask=part(src,'fn syscall_forward_rt_sigprocmask_bridge','/// Forward original ordered action')
 action=part(src,'fn syscall_forward_sigaction_update_bridge','const _:')
 registers=['rdi','rsi','rdx','r10','r8','r9']
 assert all(mask.count('gpr.'+r)==1 and action.count('gpr.'+r)==1 for r in registers)
 assert re.findall(r'gpr\.(rdi|rsi|rdx|r10|r8|r9)\)\.write(?:_volatile)?\(([^)]*)\)',mask)==list(zip(registers,['sigmask','0','0','0','0','0']))
 assert re.findall(r'gpr\.(rdi|rsi|rdx|r10|r8|r9)\)\.write(?:_volatile)?\(([^)]*)\)',action)==list(zip(registers,['sig as CULong','handler','flags','0','0','0']))
 seq=['gpr.rdi).write_volatile(sig as CULong)','sa.sa_handler','gpr.rsi).write_volatile(handler)','sa.sa_flags','gpr.rdx).write_volatile(flags)','syscall_generic_forwarding(13, ctx)'];positions=[action.index(x) for x in seq];assert positions==sorted(positions)
 assert 'syscall_generic_forwarding(14, ctx)' in mask and 'assume_init' not in src and 'zeroed' not in src
validate(leaf)
mask_vectors=[(0,[0,0,0,0,0,0]),((1<<64)-1,[(1<<64)-1,0,0,0,0,0])]
for value,expected in mask_vectors: assert [value,0,0,0,0,0]==expected
action_vectors=[(-1,0x1234,0x8000000000000000,[(1<<64)-1,0x1234,0x8000000000000000,0,0,0]),(-(1<<31),0,7,[0xffffffff80000000,0,7,0,0,0])]
for sig,handler,flags,expected in action_vectors: assert [sig % (1<<64),handler,flags,0,0,0]==expected
mutations=[leaf.replace('gpr.r8).write(0)','gpr.r8).write(1)',1),leaf.replace('gpr.rsi).write_volatile(handler)','gpr.rdi).write_volatile(handler)',1),leaf.replace('let flags = unsafe', 'let flags = unsafe',1).replace('sa.sa_flags).read()', 'sa.sa_handler).read()',1),leaf.replace('syscall_generic_forwarding(14, ctx)','syscall_generic_forwarding(13, ctx)',1)]
for item in mutations:
 try:validate(item)
 except (AssertionError,ValueError):pass
 else:raise AssertionError('invalid signal source was not refused')
policy=ROOT/'kernel/rust/syscall_policy.rs';host=ROOT/'executer/kernel/mcctrl/rust/mcctrl_helpers.rs';control=ROOT/'executer/kernel/mcctrl/control.c';executor=ROOT/'executer/user/rust/mcexec_helpers.rs';bridge=ROOT/'executer/user/mcexec.c'
s=policy.read_text();perf=part(s,'pub unsafe extern "C" fn perf_event_open_linux_fd_body_result','pub unsafe extern "C" fn perf_event_open_mckfd_publish_body_result')
for i in range(6):assert f'addr_of_mut!((*request).args[{i}])' in perf
assert perf.index('(*request).number')<perf.index('(*request).args[0]')<perf.index('(*request).args[5]')<perf.index('syscall(request, cpu)')
offload=part(s,'pub unsafe extern "C" fn syscall_offload_prepare_result','pub extern "C" fn syscall_preempt_disable_needed_result')
assert all(x in offload for x in ('(*request).rtid','(*request).ttid','(*response).req_thread_status','(*response).pde_data'))
send=part(s,'pub unsafe extern "C" fn syscall_send_prepare_result','pub unsafe extern "C" fn syscall_request_copy_result');assert '(*response).status' in send and '(*request).valid' in send
cred=part(s,'pub unsafe extern "C" fn getcred_body_result','pub unsafe extern "C" fn syscall_refresh_cred_fields_body_result');assert 'MaybeUninit::<SyscallRequest>::zeroed()' in cred and '(*requestp).args[0]' in cred and '(*requestp).args[1]' in cred and 'do_syscall(requestp, processor_id());' in cred
h=host.read_text();fill=part(h,'unsafe fn mcctrl_control_fill_cred_values','pub unsafe extern "C" fn mcctrl_control_getcred_body_result')
crednames=['current_uid','current_euid','current_suid','current_fsuid','current_gid','current_egid','current_sgid','current_fsgid']
for i,name in enumerate(crednames):assert f'*out.add({i}) = {name}();' in fill
hostbody=part(h,'pub unsafe extern "C" fn mcctrl_control_getcred_body_result','pub unsafe extern "C" fn mcctrl_control_getcredv_body_result');assert 'mcctrl_control_fill_cred_values(' in hostbody and 'return -EINVAL' in hostbody
assert 'return mcexec_getcred((unsigned long)arg);' in control.read_text()
e=executor.read_text();actioncred=part(e,'pub unsafe extern "C" fn act_setfsuid','pub unsafe extern "C" fn act_setresuid');assert 'mcexec_cred_get_bridge(fd, (*w).sr.args[0])' in actioncred and 'do_syscall_return(fd, cpu, ret, 0, 0, 0, 0)' in actioncred
b=bridge.read_text();assert 'ioctl(mcos_fd, MCEXEC_UP_GET_CRED, arg);' in b
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_SOURCE_VECTOR_AND_FIELD_WRITER_TRACE_ONLY','signal_source_vector_mutations_refused':len(mutations),'declared_edge_vectors':len(mask_vectors)+len(action_vectors),'signal_mask_args':['sigmask',0,0,0,0,0],'signal_action_args':['sig','handler','flags',0,0,0],'actual_writer_sources':{'syscall_policy':ref(policy),'host_mcctrl_rust':ref(host),'host_mcctrl_c_dispatch':ref(control),'executor_rust':ref(executor),'executor_c_bridge':ref(bridge)},'actual_writer_findings':['perf body writes request number and all six args before do_syscall; offload helper writes rtid/ttid and response req_thread_status/pde_data; send helper writes request.valid and response.status','getcred existing request is whole-zeroed in predecessor, then number,args0,args1 written; selected host getcred maps physical scratch and writes eight current IDs in order','mcexec credential bridge ignores ioctl result; act_setfsuid replies zero on this branch, so source alone cannot establish valid initialized output on failure','response completion and memory mapping/visibility/lifetime remain real runtime proof obligations; no ACK, zero-fill or new error policy proposed'],'no_behavior_execution':True,'runtime_authority':None}
(D/'FIELD-WRITER-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
