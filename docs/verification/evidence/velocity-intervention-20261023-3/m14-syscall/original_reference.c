/* Functional McKernel OS/Rust equivalence fixture; no security testing. */
#include <stddef.h>
#include <string.h>
#include <errno.h>
typedef void ihk_mc_user_context_t;
struct mckfd {
	struct mckfd *next;
	int fd;
	int sig_no;
	long data;
	void *opt;
	long (*read_cb)(struct mckfd *, ihk_mc_user_context_t *);
	int (*ioctl_cb)(struct mckfd *, ihk_mc_user_context_t *);
	long (*mmap_cb)(struct mckfd *, ihk_mc_user_context_t *);
	int (*close_cb)(struct mckfd *, ihk_mc_user_context_t *);
	int (*fcntl_cb)(struct mckfd *, ihk_mc_user_context_t *);
	int (*dup_cb)(struct mckfd *, ihk_mc_user_context_t *);
};

struct process { unsigned int mckfd_lock; struct mckfd *mckfd; };
struct thread { struct process *proc; };
extern void *fixture_c_alloc(int, unsigned long, const char *, int);
extern long fixture_lock(void *);
extern void fixture_unlock(void *, long);
#define IHK_MC_AP_NOWAIT 2UL
#define kmalloc_tracked fixture_c_alloc
#define ihk_mc_spinlock_lock fixture_lock
#define ihk_mc_spinlock_unlock fixture_unlock
#define syscall_signalfd_publish_bridge original_c_signalfd_publish_bridge
long
syscall_signalfd_publish_bridge(void *threadp, int fd,
		const unsigned long *maskp, int create)
{
	struct thread *thread = threadp;
	struct process *proc = thread->proc;
	struct mckfd *sfd;
	long irqstate;

	if (create) {
		sfd = kmalloc_tracked(sizeof(struct mckfd), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if (!sfd)
			return -ENOMEM;
		memset(sfd, '\0', sizeof(struct mckfd));
		sfd->fd = fd;
		irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
		sfd->next = proc->mckfd;
		proc->mckfd = sfd;
	} else {
		irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
		for (sfd = proc->mckfd; sfd; sfd = sfd->next) {
			if (sfd->fd == fd)
				break;
		}
		if (!sfd) {
			ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
			return -EINVAL;
		}
	}

	memcpy(&sfd->data, maskp, sizeof(*maskp));
	ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
	return sfd->fd;
}
