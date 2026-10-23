/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <ihk/cpu.h>
#include <registers.h>
extern void init_pstate_and_turbo(void);
extern int no_turbo;
extern int x86_running_on_kvm_bridge(void);
extern void x86_cpuid6_bridge(unsigned long *, unsigned long *);
extern unsigned long x86_read_msr_bridge(int);
extern void x86_write_msr_bridge(int,unsigned long);
_Static_assert(__builtin_types_compatible_p(__typeof__(&init_pstate_and_turbo),void(*)(void)),"public complete entry ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(no_turbo),int),"existing boot data ABI");
_Static_assert(sizeof(int)==4&&sizeof(unsigned long)==8,"LP64 scalar ABI");
_Static_assert(MSR_PLATFORM_INFO==0xce&&MSR_NHM_TURBO_RATIO_LIMIT==0x1ad&&MSR_IA32_PERF_CTL==0x199&&MSR_IA32_ENERGY_PERF_BIAS==0x1b0,"actual MSR constants");
