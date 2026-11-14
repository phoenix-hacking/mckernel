#ifndef SETTID_FIXTURE_H
#define SETTID_FIXTURE_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <limits.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include "memconst.h"
struct syscall_request {
	/* TID of requesting thread */
	int rtid;
	/*
	 * TID of target thread. Remote page fault response needs to designate the
	 * thread that must serve the request, 0 indicates any thread from the pool
	 */
	int ttid;
	unsigned long valid;
	unsigned long number;
	unsigned long args[6];
};
_Static_assert(sizeof(struct syscall_request)==72,"request size");
_Static_assert(_Alignof(struct syscall_request)==8,"request alignment");
_Static_assert(offsetof(struct syscall_request,rtid)==0,"rtid offset");
_Static_assert(offsetof(struct syscall_request,ttid)==4,"ttid offset");
_Static_assert(offsetof(struct syscall_request,valid)==8,"valid offset");
_Static_assert(offsetof(struct syscall_request,number)==16,"number offset");
_Static_assert(offsetof(struct syscall_request,args)==24,"args offset");
_Static_assert(sizeof(int)==4 && sizeof(long)==8,"scalar widths");
enum { __NR_gettid = 186 };
struct thread { int unused; };
typedef int (*syscall_get_cpu_fn_t)(void);
typedef long (*syscall_request_call_fn_t)(struct syscall_request *request,
		int cpu);
typedef unsigned long (*syscall_virt_to_phys_fn_t)(void *addr);
unsigned long fixture_virt_to_phys(void *);
int fixture_get_cpu(void);
long fixture_do_syscall(struct syscall_request *,int);
int fixture_kprintf(const char *,...);
#define virt_to_phys fixture_virt_to_phys
#define ihk_mc_get_processor_id fixture_get_cpu
#define do_syscall fixture_do_syscall
#define kprintf fixture_kprintf
int run_original(int,int *);
int run_candidate(int,int *);
#endif
