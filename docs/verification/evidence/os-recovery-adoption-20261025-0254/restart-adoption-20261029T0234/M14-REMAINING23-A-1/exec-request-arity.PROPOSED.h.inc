/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Declarations only, no implementation/selection; transport must authorize seed. */
struct f03_exec_phase1_transport_seed {
    int rtid, ttid;
    unsigned long valid, unused_arg5;
};
extern void f03_execveat_phase1_declared_v1(struct syscall_request *, unsigned long,
    int, const void *, unsigned long, int, struct f03_exec_phase1_transport_seed);
extern void f03_execveat_phase2_declared_v1(struct syscall_request *, unsigned long,
    unsigned long, unsigned long);

const unsigned long f03_exec_request_arity_C_ABI_v1[13] = {
    sizeof(struct syscall_request), _Alignof(struct syscall_request),
    __builtin_offsetof(struct syscall_request, rtid), __builtin_offsetof(struct syscall_request, ttid),
    __builtin_offsetof(struct syscall_request, valid), __builtin_offsetof(struct syscall_request, number),
    __builtin_offsetof(struct syscall_request, args),
    sizeof(struct f03_exec_phase1_transport_seed), _Alignof(struct f03_exec_phase1_transport_seed),
    __builtin_offsetof(struct f03_exec_phase1_transport_seed, rtid),
    __builtin_offsetof(struct f03_exec_phase1_transport_seed, ttid),
    __builtin_offsetof(struct f03_exec_phase1_transport_seed, valid),
    __builtin_offsetof(struct f03_exec_phase1_transport_seed, unused_arg5),
};
