/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Real complete selected C TU + public full-signature ABI/allocated C caller.
 * Witness excluded from the production partial to avoid duplicate whole TU.
 */
#include "candidate/syscall.c"
_Static_assert(sizeof(long)==8 && sizeof(void *)==8 && sizeof(int)==4,"realLP64");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_native_signal_restore_fp_bridge),long (*)(unsigned long,int)),"public native FP restore ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_native_signal_reset_fp_bridge),long (*)(void)),"existing CPU reset wrapper ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_native_signal_mxcsr_mask_bridge),unsigned int (*)(void)),"existing CPU MXCSR wrapper ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&native_xrstor_checked),long (*)(const unsigned char *,uint64_t)),"checked XRSTOR ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kmalloc_tracked),void *(*)(int,ihk_mc_ap_flag,char *,int)),"actual tracked allocator ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&copy_from_user),int (*)(void *,const void *,size_t)),"actual usercopy ABI");
_Static_assert(IHK_MC_AP_NOWAIT==2 && 65536+63<=2147483647,"real allocator flag/extent");
__attribute__((noinline,used)) long f06_actual_native_FP_C_caller(unsigned long user_address,int size)
{return arch_native_signal_restore_fp_bridge(user_address,size);}
