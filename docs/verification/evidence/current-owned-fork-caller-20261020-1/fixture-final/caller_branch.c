#include <stddef.h>
struct thread;
#ifdef MCKERNEL_NATIVE_FORK_OWNED_TRANSACTION
struct owned_fork_caller_outcome {
    unsigned int disposition;
    int error;
    struct { unsigned int slot, reserved; unsigned long epoch; } handle;
};
extern int process_fork_owned_caller_current_v1(struct thread *, struct thread *,
        int, unsigned long, struct owned_fork_caller_outcome *);
#endif
extern int clone_host_parent_flags_result(int clone_flags, int ppid_parent_pid);
_Static_assert(sizeof(struct owned_fork_caller_outcome)==24,"outcome ABI");
_Static_assert(offsetof(struct owned_fork_caller_outcome,handle)==8,"outcome handle offset");
static unsigned long probe[4];
void reset_caller_probe(void){for(unsigned int i=0;i<4;i++)probe[i]=0;}
unsigned long caller_probe_counts(unsigned int i){return i<4?probe[i]:~0UL;}
long invoke_actual_owned_caller_branch(struct thread *old,struct thread *new,int cpuid){
    int clone_flags=0,err=0;
    struct parent_probe{int pid;} parent={1};
    struct process_probe{struct parent_probe *ppid_parent;} process={&parent},*oldproc=&process;
    {
#ifdef MCKERNEL_NATIVE_FORK_OWNED_TRANSACTION
        struct owned_fork_caller_outcome outcome;
        err = process_fork_owned_caller_current_v1(old, new, cpuid,
                clone_host_parent_flags_result(clone_flags,
                    oldproc->ppid_parent->pid), &outcome);
        if (err)
            goto destroy_thread;
        if (outcome.disposition == 0) {
            err = outcome.error;
            goto destroy_thread;
        }
        /* Existing registry owns request/parent/child/VM/reserved CPU. A first
         * positive receipt supplies no runnable/cleanup authority. */
        return outcome.error;
#endif

    }
    probe[3]++; /* fixture continuation toward original chain/runq */
    return 0;
destroy_thread:
    probe[0]++;probe[1]++; /* adapters: selected cleanup edge, no destructor */
    probe[2]++;           /* adapter: existing release_cpuid edge */
    return err;
}
