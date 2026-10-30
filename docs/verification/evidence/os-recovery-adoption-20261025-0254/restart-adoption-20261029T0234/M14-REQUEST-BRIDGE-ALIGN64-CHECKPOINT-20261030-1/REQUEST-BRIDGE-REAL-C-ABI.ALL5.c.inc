/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Test-only suffix for the exact selected syscall.c translation unit.
 * Test-only object: type assertions and five used reference slots; never link into a production image. */
#if !defined(MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS) || !defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS)
#error request_bridge_witness_requires_paired_existing_c_selectors
#endif
extern long syscall_policy_do_syscall2_bridge(int, unsigned long, unsigned long);
typedef long (*f03_policy_two_sig)(int, unsigned long, unsigned long);
typedef long (*f03_policy_three_sig)(int, unsigned long, unsigned long, unsigned long);
typedef int (*f03_wait_sig)(int, int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_policy_do_syscall2_bridge), f03_policy_two_sig), "policy-two C declaration");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_policy_do_syscall3_bridge), f03_policy_three_sig), "policy-three C declaration");
_Static_assert(__builtin_types_compatible_p(__typeof__(&wait_host_wait4_bridge), f03_wait_sig), "wait C declaration");
_Static_assert(__builtin_types_compatible_p(__typeof__(f03_wait_c_dependencies.host_wait4), f03_wait_sig), "wait selected consumer field");
_Static_assert(sizeof(int) == 4 && sizeof(long) == 8 && sizeof(unsigned long) == 8, "selected scalar ABI");
_Static_assert((unsigned long)(int)-1 == ~0UL, "signed int to unsigned long conversion");
_Static_assert(__NR_wait4 == 61, "selected x86 wait4 number");
_Static_assert(sizeof(struct syscall_request) == 72 && _Alignof(struct syscall_request) == 8, "request size and alignment");
_Static_assert(__builtin_offsetof(struct syscall_request, rtid) == 0 && __builtin_offsetof(struct syscall_request, ttid) == 4, "request IDs");
_Static_assert(__builtin_offsetof(struct syscall_request, valid) == 8 && __builtin_offsetof(struct syscall_request, number) == 16, "request valid and number");
_Static_assert(__builtin_offsetof(struct syscall_request, args) == 24 && sizeof(((struct syscall_request *)0)->args) == 48, "six argument words");

/* Direct C callers use the actual selected translation-unit declarations. */
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_do_syscall2_bridge), f03_policy_two_sig), "direct-two C declaration");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_do_syscall3_bridge), f03_policy_three_sig), "direct-three C declaration");
/* Test-only relocation roots force all five names to be link-relevant. */
static f03_policy_two_sig const f03_witness_direct_two __attribute__((used)) = &syscall_do_syscall2_bridge;
static f03_policy_two_sig const f03_witness_policy_two __attribute__((used)) = &syscall_policy_do_syscall2_bridge;
static f03_policy_three_sig const f03_witness_direct_three __attribute__((used)) = &syscall_do_syscall3_bridge;
static f03_policy_three_sig const f03_witness_policy_three __attribute__((used)) = &syscall_policy_do_syscall3_bridge;
static f03_wait_sig const f03_witness_wait __attribute__((used)) = &wait_host_wait4_bridge;
