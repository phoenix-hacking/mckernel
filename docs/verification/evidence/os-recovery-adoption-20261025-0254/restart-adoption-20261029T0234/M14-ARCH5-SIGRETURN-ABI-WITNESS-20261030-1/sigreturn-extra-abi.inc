/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Compile-only data in actual native arch TU after struct sigsp. Not production. */
#ifndef MCKERNEL_NATIVE_SIGNAL_STACK
#error "native signal frame required"
#endif
const unsigned long sigreturn_extra_c_geometry[] __attribute__((used,section(".sigreturn_extra_c"))) = {
    __builtin_offsetof(struct sigsp, flags), /* 0: frame.flags */
    __builtin_offsetof(struct sigsp, link), /* 1: frame.link */
    __builtin_offsetof(struct sigsp, sigstack), /* 2: frame.sigstack */
    __builtin_offsetof(struct sigsp, regs), /* 3: frame.regs */
    __builtin_offsetof(struct sigsp, fpregs), /* 4: frame.fpregs */
    __builtin_offsetof(struct sigsp, reserve), /* 5: frame.reserve */
    __builtin_offsetof(struct sigsp, sigmask), /* 6: frame.sigmask */
    __builtin_offsetof(struct sigsp, info), /* 7: frame.info */
    __builtin_offsetof(stack_t, ss_sp), /* 8: stack.ss_sp */
    __builtin_offsetof(stack_t, ss_flags), /* 9: stack.ss_flags */
    __builtin_offsetof(stack_t, ss_size), /* 10: stack.ss_size */
    sizeof(stack_t), /* 11: stack.size */
    __alignof__(stack_t), /* 12: stack.align */
    __builtin_offsetof(struct thread, vm), /* 13: thread.vm */
    __builtin_offsetof(struct process_vm, region), /* 14: process_vm.region */
    __builtin_offsetof(struct vm_regions, user_start), /* 15: vm_regions.user_start */
    __builtin_offsetof(struct vm_regions, user_end), /* 16: vm_regions.user_end */
    __builtin_offsetof(struct x86_user_context, gpr), /* 17: context.gpr */
    __builtin_offsetof(struct x86_user_context, gpr.r8), /* 18: context.gpr.r8 */
    __builtin_offsetof(struct x86_user_context, gpr.r9), /* 19: context.gpr.r9 */
    __builtin_offsetof(struct x86_user_context, gpr.r10), /* 20: context.gpr.r10 */
    __builtin_offsetof(struct x86_user_context, gpr.r11), /* 21: context.gpr.r11 */
    __builtin_offsetof(struct x86_user_context, gpr.r12), /* 22: context.gpr.r12 */
    __builtin_offsetof(struct x86_user_context, gpr.r13), /* 23: context.gpr.r13 */
    __builtin_offsetof(struct x86_user_context, gpr.r14), /* 24: context.gpr.r14 */
    __builtin_offsetof(struct x86_user_context, gpr.r15), /* 25: context.gpr.r15 */
    __builtin_offsetof(struct x86_user_context, gpr.rdi), /* 26: context.gpr.rdi */
    __builtin_offsetof(struct x86_user_context, gpr.rsi), /* 27: context.gpr.rsi */
    __builtin_offsetof(struct x86_user_context, gpr.rbp), /* 28: context.gpr.rbp */
    __builtin_offsetof(struct x86_user_context, gpr.rbx), /* 29: context.gpr.rbx */
    __builtin_offsetof(struct x86_user_context, gpr.rdx), /* 30: context.gpr.rdx */
    __builtin_offsetof(struct x86_user_context, gpr.rax), /* 31: context.gpr.rax */
    __builtin_offsetof(struct x86_user_context, gpr.rcx), /* 32: context.gpr.rcx */
    __builtin_offsetof(struct x86_user_context, gpr.rsp), /* 33: context.gpr.rsp */
    __builtin_offsetof(struct x86_user_context, gpr.rip), /* 34: context.gpr.rip */
    __builtin_offsetof(struct x86_user_context, gpr.rflags), /* 35: context.gpr.rflags */
    __builtin_offsetof(struct x86_user_context, gpr.orig_rax), /* 36: context.gpr.orig_rax */
    __builtin_offsetof(struct sigsp, regs[15]), /* 37: frame.regs.rsp */
    __builtin_offsetof(struct sigsp, regs[16]), /* 38: frame.regs.rip */
    __builtin_offsetof(struct sigsp, regs[17]), /* 39: frame.regs.rflags */
};
_Static_assert(sizeof(sigreturn_extra_c_geometry) / sizeof(unsigned long) == 40, "geometry length");
