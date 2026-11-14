/* Literal original do_execveat fragment in a field-only C oracle.
 * This does not prove the production C Thread layout or current caller admission.
 */
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define _NSIG 64
#define SIG_DFL ((void *)0)
#define SIG_IGN ((void *)1)
#define SS_DISABLE 2
struct sigaction { void *sa_handler; unsigned long sa_flags; void *sa_restorer; unsigned long sa_mask; };
struct k_sigaction { struct sigaction sa; };
struct sigcommon { unsigned char prefix[72]; struct k_sigaction action[64]; };
struct sigstack { void *ss_sp; int ss_flags; int padding; size_t ss_size; };
struct thread { struct sigcommon *sigcommon; struct sigstack sigstack; };
extern void oracle_observe_fp(void *, void *);
static struct thread *active;
static void clear_fp_regs(void) { oracle_observe_fp(active->sigcommon, &active->sigstack); }
_Static_assert(sizeof(struct sigaction) == 32, "sigaction field ABI");
_Static_assert(sizeof(struct sigstack) == 24, "sigstack field ABI");
void exec_reset_c_reference(void *common, void *stack) {
    struct thread holder = { .sigcommon = common };
    struct thread *thread = &holder;
    int i;
    memcpy(&holder.sigstack, stack, sizeof(holder.sigstack));
    active = thread;
	for(i = 0; i < _NSIG; i++){
		if(thread->sigcommon->action[i].sa.sa_handler != SIG_IGN &&
		   thread->sigcommon->action[i].sa.sa_handler != SIG_DFL)
			thread->sigcommon->action[i].sa.sa_handler = SIG_DFL;
	}

	/* Reset floating-point environment to default. */
	clear_fp_regs();

	/* Reset sigaltstack to default */
	thread->sigstack.ss_sp = NULL;
	thread->sigstack.ss_flags = SS_DISABLE;
	thread->sigstack.ss_size = 0;

    memcpy(stack, &holder.sigstack, sizeof(holder.sigstack));
    active = NULL;
}
size_t c_action_offset(void) { return offsetof(struct sigcommon, action); }
