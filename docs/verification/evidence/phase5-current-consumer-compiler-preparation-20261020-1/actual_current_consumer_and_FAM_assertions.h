/* Assertions appended to the entire actual syscall.c; real declarations only. */
_Static_assert(__builtin_offsetof(struct address_space,nslots)==164,"real C nslots matches Rust offset");
_Static_assert(__builtin_offsetof(struct address_space,pids)==168,"real C flexible PID array offset");
_Static_assert(__builtin_offsetof(struct address_space,pids)==__builtin_offsetof(struct address_space,nslots)+sizeof(int),"real C PID tail follows nslots");
_Static_assert(sizeof(((struct address_space *)0)->pids[0])==4,"real PID slot width matches Rust CInt");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct address_space *)0)->pids[0]),int),"real PID slot type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&clone_thread),struct thread *(*)(struct thread *,unsigned long,unsigned long,int)),"real constructor prototype");
#ifdef MCKERNEL_NATIVE_FORK_OWNED_TRANSACTION
_Static_assert(sizeof(struct owned_fork_caller_outcome)==24,"real Rust result ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_fork_owned_caller_runnable_current_v2),int(*)(struct thread *,struct thread *,int,unsigned long,void *,int,int,unsigned long,struct owned_fork_caller_outcome *)),"real libc child-TID consumer ABI");
#endif

/* Append after the ENTIRE genuine current syscall.c; no declarations replaced. */
_Static_assert(__builtin_offsetof(struct address_space, nslots) == 164,
               "actual C nslots offset must match actual Rust prefix");
_Static_assert(__builtin_offsetof(struct address_space, pids) == 168,
               "actual C FAM offset must match actual Rust nslots field end");
_Static_assert(__builtin_offsetof(struct address_space, pids) ==
               __builtin_offsetof(struct address_space, nslots) + sizeof(int),
               "actual C PID FAM must immediately follow nslots");
_Static_assert(sizeof(int) == 4 && _Alignof(int) == 4,
               "actual C int width/alignment must match Rust CInt");
_Static_assert(sizeof(((struct address_space *)0)->nslots) == sizeof(int) &&
               sizeof(((struct address_space *)0)->pids[0]) == sizeof(int),
               "actual C slot and count widths");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct address_space *)0)->nslots), int) &&
               __builtin_types_compatible_p(__typeof__(((struct address_space *)0)->pids[0]), int),
               "actual C slot and count types");
_Static_assert(_Alignof(struct address_space) == 8 && sizeof(unsigned long) == 8,
               "actual C prefix and witness machine-word alignment/width");
_Static_assert(__builtin_offsetof(struct address_space, pids) % _Alignof(int) == 0,
               "actual C first PID alignment");
/* Evidence only: this compiler-feedback object is not a production link input. */
const unsigned long mckernel_phase5_c_fam_layout[5]
__attribute__((used, section(".mckernel_fam_layout"))) = {
    __builtin_offsetof(struct address_space, nslots),
    __builtin_offsetof(struct address_space, pids),
    sizeof(int), _Alignof(int), _Alignof(struct address_space)
};
