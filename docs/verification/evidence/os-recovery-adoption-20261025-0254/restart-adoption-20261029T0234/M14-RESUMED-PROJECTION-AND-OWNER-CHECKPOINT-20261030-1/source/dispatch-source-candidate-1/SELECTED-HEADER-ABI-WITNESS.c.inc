/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Append to the private selected kernel/syscall.c TU for a separately admitted
 * compile. This source emits data only; it is NOT a result or an admission.
 * Do not substitute this source for actual emitted C/Rust object comparison.
 */
#ifndef MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED
#error Witness_requires_private_do_syscall_metadata_selection
#endif
#ifndef MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE
#error Witness_requires_private_util_thread_metadata_selection
#endif
#define F03_S(t) sizeof(t)
#define F03_A(t) __alignof__(t)
#define F03_O(t,f) __builtin_offsetof(t,f)
const unsigned long f03_do_syscall_C_ABI_v1[29] __attribute__((used)) = {
 F03_S(struct syscall_request), F03_A(struct syscall_request),
 F03_O(struct syscall_request,rtid), F03_O(struct syscall_request,ttid),
 F03_O(struct syscall_request,valid), F03_O(struct syscall_request,number),
 F03_O(struct syscall_request,args),
 F03_S(struct syscall_response), F03_A(struct syscall_response),
 F03_O(struct syscall_response,status), F03_O(struct syscall_response,req_thread_status),
 F03_O(struct syscall_response,ret), F03_O(struct syscall_response,pde_data),
 F03_S(struct ihk_os_cpu_monitor), F03_A(struct ihk_os_cpu_monitor),
 F03_O(struct ihk_os_cpu_monitor,status), F03_O(struct ihk_os_cpu_monitor,counter),
 F03_S(struct cpu_local_var), F03_A(struct cpu_local_var),
 F03_O(struct cpu_local_var,current), F03_O(struct cpu_local_var,monitor),
 F03_S(struct thread), F03_A(struct thread), F03_O(struct thread,tid),
 F03_O(struct thread,proc), F03_O(struct thread,profile),
 F03_O(struct thread,in_syscall_offload),
 F03_O(struct process,pid), F03_O(struct process,nohost),
};
/* Kattr and saved-context prefix are block-local in their original C bodies.
 * These explicit witness-only mirrors compare their exact stated fields, not
 * all saved-context bytes. Original C definitions must remain source-bound.
 */
struct f03_kattr_witness { long parent_cpuid; struct uti_attr attr; };
struct f03_context_prefix_witness { volatile int cond; int fregsize; };
struct f03_refill_witness { int uti_refill_tid; };
const unsigned long f03_util_thread_C_ABI_v1[23] __attribute__((used)) = {
 F03_S(struct f03_util_thread_layout), F03_A(struct f03_util_thread_layout),
 F03_S(struct f03_util_thread_origins), F03_A(struct f03_util_thread_origins),
 F03_S(struct f03_kattr_witness), F03_A(struct f03_kattr_witness),
 F03_O(struct f03_kattr_witness,parent_cpuid), F03_O(struct f03_kattr_witness,attr),
 F03_S(struct uti_attr), F03_A(struct uti_attr),
 F03_S(struct syscall_request), F03_A(struct syscall_request),
 F03_S(int), F03_S(long), F03_S(unsigned long),
 F03_O(struct f03_context_prefix_witness,cond), F03_S(unsigned long),
 F03_S(struct uti_ctx), F03_A(struct uti_ctx), F03_O(struct uti_ctx,ctx),
 F03_O(struct uti_ctx,uti_refill_tid),
 F03_S(struct f03_refill_witness), F03_A(struct f03_refill_witness),
};
const unsigned long f03_request_wire_C_ABI_v1[4] __attribute__((used)) = {
 __NR_wait4, __NR_sched_setaffinity, sizeof(struct syscall_request),
 __alignof__(struct syscall_request),
};
#undef F03_S
#undef F03_A
#undef F03_O
