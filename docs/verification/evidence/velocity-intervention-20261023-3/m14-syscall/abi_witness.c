/* Functional OS/Rust migration only; no security testing.
 * Compile later with the exact supported kernel/syscall.c include/config profile.
 * This is the independent real-header witness, separate from host C fixture views.
 */
#include <process.h>
#define OFF(T,F) __builtin_offsetof(T,F)
_Static_assert(sizeof(long)==8 && sizeof(unsigned long)==8, "mask word ABI");
_Static_assert(sizeof(struct mckfd)==80, "mckfd size");
_Static_assert(OFF(struct mckfd,next)==0, "mckfd next");
_Static_assert(OFF(struct mckfd,fd)==8, "mckfd fd");
_Static_assert(OFF(struct mckfd,sig_no)==12, "zeroed sig_no/Rust padding");
_Static_assert(OFF(struct mckfd,data)==16, "mckfd data");
_Static_assert(OFF(struct process,mckfd_lock)==1284, "process lock");
_Static_assert(OFF(struct process,mckfd)==1288, "process list head");
_Static_assert(OFF(struct thread,proc)==4304, "thread process");
