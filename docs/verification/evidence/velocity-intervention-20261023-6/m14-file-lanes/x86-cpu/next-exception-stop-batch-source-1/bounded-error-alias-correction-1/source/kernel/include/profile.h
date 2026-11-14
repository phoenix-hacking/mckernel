#ifndef __PROCESS_PROFILE_H_
#define __PROCESS_PROFILE_H_

#ifdef PROFILE_ENABLE
#define PROFILE_SYSCALL_MAX                          2000
#define PROFILE_OFFLOAD_MAX   (PROFILE_SYSCALL_MAX << 1)
#define PROFILE_EVENT_MIN            PROFILE_OFFLOAD_MAX

#define PROF_JOB                       0x40000000
#define PROF_PROC                      0x80000000
#define PROF_CLEAR                           0x01
#define PROF_ON                              0x02
#define PROF_OFF                             0x04
#define PROF_PRINT                           0x08

struct profile_event {
	uint32_t cnt;
	uint64_t tsc;
};

/*
 * The layout of profile events is as follows:
 * [0,PROFILE_SYSCALL_MAX) - syscalls
 * [PROFILE_SYSCALL_MAX,PROFILE_OFFLOAD_MAX) - syscall offloads
 * [PROFILE_OFFLOAD_MAX,PROFILE_EVENT_MAX) - general events
 *
 * XXX: Make sure to fill in prof_event_names in profile.c
 * for each added profiled event.
 */
enum profile_event_type {
	PROFILE_tlb_invalidate = PROFILE_EVENT_MIN,
	PROFILE_page_fault,
	PROFILE_page_fault_anon_clr,
	PROFILE_page_fault_file,
	PROFILE_page_fault_dev_file,
	PROFILE_page_fault_file_clr,
	PROFILE_remote_page_fault,
	PROFILE_mpol_alloc_missed,
	PROFILE_mmap_anon_contig_phys,
	PROFILE_mmap_anon_straight,
	PROFILE_mmap_anon_not_straight,
	PROFILE_mmap_anon_no_contig_phys,
	PROFILE_mmap_regular_file,
	PROFILE_mmap_device_file,
	PROFILE_tofu_stag_alloc,
	PROFILE_tofu_stag_alloc_new_steering,
	PROFILE_tofu_stag_alloc_new_steering_alloc_mbpt,
	PROFILE_tofu_stag_alloc_new_steering_update_mbpt,
	PROFILE_tofu_stag_free_stags,
	PROFILE_tofu_stag_free_stag,
	PROFILE_tofu_stag_free_stag_pre,
	PROFILE_tofu_stag_free_stag_cqflush,
	PROFILE_tofu_stag_free_stag_dealloc,
	PROFILE_tofu_stag_free_stag_dealloc_free_pages,
	PROFILE_EVENT_MAX	/* Should be the last event type */
};

#ifdef __KERNEL__
struct thread;
struct process;

enum profile_event_type profile_syscall2offload(enum profile_event_type sc);
void profile_event_add(enum profile_event_type type, uint64_t tsc);
void profile_print_thread_stats(struct thread *thread);
void profile_print_proc_stats(struct process *proc);
void profile_print_job_stats(struct process *proc);
void profile_accumulate_events(struct thread *thread, struct process *proc);
int profile_accumulate_and_print_job_events(struct process *proc);
int profile_alloc_events(struct thread *thread);
void profile_dealloc_thread_events(struct thread *thread);
void profile_dealloc_proc_events(struct process *proc);

#else // User space interface
#include <unistd.h>
#include <sys/syscall.h>

#define __NR_profile                   PROFILE_EVENT_MAX

/* Per-thread */
void mckernel_profile_thread_on(void);
void mckernel_profile_thread_off(void);
void mckernel_profile_thread_print(void);
void mckernel_profile_thread_print_off(void);

/* Per-process */
void mckernel_profile_process_on(void);
void mckernel_profile_process_off(void);
void mckernel_profile_process_print(void);
void mckernel_profile_process_print_off(void);

/* Per-job */
void mckernel_profile_job_on(void);
void mckernel_profile_job_off(void);
void mckernel_profile_job_print(void);
void mckernel_profile_job_print_off(void);

#endif // __KERNEL__
#endif // PROFILE_ENABLE



#endif // __PROCESS_PROFILE_H_
