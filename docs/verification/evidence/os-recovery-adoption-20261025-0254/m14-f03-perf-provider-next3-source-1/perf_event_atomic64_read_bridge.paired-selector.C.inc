#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_PERF_PROVIDER_NEXT3_BRIDGES)
extern long syscall_atomic64_read_bridge(void *value);
#define perf_event_atomic64_read_bridge syscall_atomic64_read_bridge
_Static_assert(sizeof(ihk_atomic64_t)==8 && __alignof__(ihk_atomic64_t)==8 && __builtin_offsetof(ihk_atomic64_t,counter64)==0, "existing atomic64 provider layout ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_atomic64_read), long (*)(const ihk_atomic64_t *)), "existing atomic64 read provider C ABI");
#else
#line 20564
static long
perf_event_atomic64_read_bridge(void *value)
{
	return ihk_atomic64_read((ihk_atomic64_t *)value);
}
#endif
#line 20569
