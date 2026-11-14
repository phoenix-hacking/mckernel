#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_PERF_PROVIDER_NEXT3_BRIDGES)
extern int perf_counter_init_raw_bridge(int counter_id, unsigned long hw_config, int mode);
_Static_assert(sizeof(unsigned long)==8 && sizeof(unsigned int)==4, "supported Rust perf init code narrowing ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_perfctr_init_raw), int (*)(int,unsigned int,int)), "selected x86 Rust provider requires original u32 code ABI");
#else
#line 20504
static int
perf_counter_init_raw_bridge(int counter_id, unsigned long hw_config, int mode)
{
	return ihk_mc_perfctr_init_raw(counter_id, hw_config, mode);
}
#endif
#line 20509
