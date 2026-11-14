"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only source/ABI/order checks; no compiler, process, guard or native operation.
"""
from pathlib import Path
import json,re,hashlib
D=Path(__file__).resolve().parent;A=D.parent;S=A/'M14-CONVERSION-FIRST-LARGE-COMPOSITION-2';B=A/'M14-CONVERSION-FIRST-COMPOSITION-1';K=A/'M14-UPGRADED-F03-REQUEST-CONSTRUCTORS-1/natural-alignment-correction-1';C=(S/'postimage/kernel/syscall.c').read_text();P=(S/'postimage/kernel/rust/syscall_policy.rs').read_text();M=(D/'postimage/kernel/CMakeLists.txt').read_text();L=(K/'postimage/kernel/rust/f03_request_constructors.rs').read_text();h=Path('/home/holden/mckernel/kernel/include/syscall.h').read_text();abi=Path('/home/holden/mckernel/kernel/rust/abi.rs').read_text();old=(S/'postimage/kernel/CMakeLists.txt').read_text();wire=(D/'QUEUE-B-WIRING.ON-LARGE-COMPOSITION.patch').read_text()
assert hashlib.sha256((S/'SOURCE-READY.json').read_bytes()).hexdigest()=='b6c1d2875e36cdd4887dddc65ad26fe1883670f8083e411b35e5b362ecc71cc4'
assert hashlib.sha256((S/'postimage/kernel/rust/syscall_policy.rs').read_bytes()).hexdigest()=='c3daed2f58bf070b1ca98a493ae5b1faad85996a2e0d6f8e327a423744e1bac2'
assert hashlib.sha256((K/'postimage/kernel/rust/f03_request_constructors.rs').read_bytes()).hexdigest()=='d1e40575145b827d7a48cbdc874aee3c3cc510d623d3eecb0c974073b1c3d070'
for sym in ('syscall_do_syscall2_bridge','syscall_policy_do_syscall2_bridge','syscall_do_syscall3_bridge','syscall_policy_do_syscall3_bridge','wait_host_wait4_bridge'):
 assert len(re.findall(r'pub unsafe extern "C" fn '+sym+r'\(',L))==1
assert L.count('forward(number, [arg0, arg1, 0, 0, 0, 0])')==2
assert L.count('forward(number, [arg0, arg1, arg2, 0, 0, 0])')==2
assert 'forward(SYS_WAIT4, [pid as CULong, 0, options as CULong, 0, 0, 0]) as CInt' in L and 'const SYS_WAIT4: CInt = 61;' in L
assert 'MaybeUninit::<SyscallRequest>::uninit()' in L and '.assume_init()' not in L and 'align(64)' not in L
for i in range(6):assert L.count('slots.add('+str(i)+').write(args['+str(i)+'])')==1
assert 'addr_of_mut!((*request).number).write(number as CULong)' in L
assert 'size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8' in L
for t in ('int rtid;', 'int ttid;', 'unsigned long valid;', 'unsigned long number;', 'unsigned long args[6];'):assert t in h[h.index('struct syscall_request {'):h.index('struct ihk_os_cpu_register {')]
for s in ('size_of::<SyscallRequest>(), 72','align_of::<SyscallRequest>(), 8','offset_of!(SyscallRequest, number), 16','offset_of!(SyscallRequest, args), 24','size_of::<IkcScdPacket>(), 128'):assert s in abi
assert 'fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;' in P
start=P.index('pub unsafe extern "C" fn send_syscall(');send=P[start:P.index('pub unsafe extern "C" fn syscall_offload_prepare_result',start)]
assert send.index('syscall_send_prepare_result(request, response)')<send.index('syscall_request_copy_result(packet_request, request)')<send.index('syscall_request_publish_result(packet_request)')
copy=P[P.index('pub unsafe extern "C" fn syscall_request_copy_result'):P.index('pub unsafe extern "C" fn syscall_request_publish_result')];assert 'size_of::<SyscallRequest>()' in copy and 'copy_nonoverlapping(' in copy
prep=P[P.index('pub unsafe extern "C" fn syscall_offload_prepare_result'):P.index('pub extern "C" fn syscall_preempt_disable_needed_result')];assert all(x in prep for x in ('(*request).rtid','(*request).ttid','(*response).req_thread_status','(*response).pde_data'))
for body in ('DO-SYSCALL','UTIL-THREAD'):
 fragment=(A/('M14-LARGE-'+body+'-REUSE-1')/'RUST-BODY.REUSED.rs.inc').read_text();assert P.count(fragment)==1
assert '(*request).args[5]), 0' in P and 'f03_util_thread_arg5_zero_candidate' in P
assert all(x in C for x in ('MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED','MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE','MCKERNEL_RUST_F03_UTIL_REQUEST_ARG5_ZERO','MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS'))
for opt in ('MCKERNEL_F03_DO_SYSCALL_SUPPORTED_EXPERIMENTAL','MCKERNEL_F03_UTIL_THREAD_WHOLE_EXPERIMENTAL'):
 assert M.count('if ('+opt+')')==2 and opt not in old and 'option('+opt not in M and 'set('+opt not in M
assert 'if (NOT MCKERNEL_F03_DEFINED_ALL_REQUEST_CALLERS_REVIEWED)' in M and 'message(FATAL_ERROR "F03 do_syscall requires reviewed initialization of all selected callers")' in M
for cfg in ('f03_do_syscall_supported_candidate','f03_util_thread_whole_candidate','f03_util_thread_arg5_zero_candidate'):assert cfg in M and cfg not in old
assert M.count('if (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)')==2
assert len(re.findall(r'^[-+](?![-+])',wire,re.M))==16
print('PASS 5 constructor exports; exact approved 6-slot vectors; x86 72/8 and packet128 source declarations; prepare-copy-publish order; two byte-reused bodies; paired experimental cfg/defines and all-caller gate. No compiler/native/runtime.')
