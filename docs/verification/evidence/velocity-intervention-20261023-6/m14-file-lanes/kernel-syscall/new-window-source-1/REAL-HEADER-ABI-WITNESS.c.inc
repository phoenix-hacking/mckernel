/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_swapout_log_bridge),void (*)(const void *,void *,size_t,int)),"swapout callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_linux_mlock_log_bridge),void (*)(unsigned long,unsigned long)),"mlock callback ABI");
_Static_assert(sizeof(size_t)==sizeof(unsigned long),"size_t formatter slot");
_Static_assert(sizeof(long)==8,"signed long formatter slot");
_Static_assert(sizeof(struct ddebug)==32,"actual debug record size");
_Static_assert(__alignof__(struct ddebug)==8,"actual debug alignment");
_Static_assert(__builtin_offsetof(struct ddebug,file)==0,"actual debug file offset");
_Static_assert(__builtin_offsetof(struct ddebug,func)==8,"actual debug function offset");
_Static_assert(__builtin_offsetof(struct ddebug,fmt)==16,"actual debug format offset");
