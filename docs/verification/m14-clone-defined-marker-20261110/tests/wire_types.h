/* Exact wire struct text from current kernel/include/syscall.h.
 * Standalone HOST protocol witness only; not a full guest/header namespace. */
#ifndef CLONE_MARKER_WIRE_TYPES_H
#define CLONE_MARKER_WIRE_TYPES_H
#include <stddef.h>
#include <stdint.h>
#include "/home/holden/mckernel/ihk/cokernel/smp/x86_64/include/ihk/memconst.h"
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

struct syscall_response {
	/* TID of the thread that requested the service */
	int ttid;
	/* TID of the mcexec thread that is serving the request */
	int stid;
	unsigned long status;
	unsigned long req_thread_status;
	long ret;
	unsigned long fault_address;
	void *pde_data;
};

struct thread;
enum { __NR_clone = 56, __NR_kill = 62 };
_Static_assert(sizeof(int)==4 && sizeof(long)==8 && sizeof(void*)==8,"actual HOST x86_64 C ABI");
_Static_assert(sizeof(struct syscall_request)==72,"real request wire size");
_Static_assert(_Alignof(struct syscall_request)==8,"real x86 natural request alignment");
_Static_assert(offsetof(struct syscall_request,rtid)==0 && offsetof(struct syscall_request,ttid)==4,"TID offsets");
_Static_assert(offsetof(struct syscall_request,valid)==8 && offsetof(struct syscall_request,number)==16 && offsetof(struct syscall_request,args)==24,"request offsets");
_Static_assert(sizeof(struct syscall_response)==48 && offsetof(struct syscall_response,ret)==24 && offsetof(struct syscall_response,pde_data)==40,"guest response extension ABI");
extern int clone_host_parent_flags_result(int,int);
extern int syscall_offload_prepare_result(struct syscall_request*,struct syscall_response*,int,int,unsigned long,int,unsigned long);
extern int syscall_send_prepare_result(struct syscall_request*,struct syscall_response*);
extern int syscall_request_copy_result(struct syscall_request*,const struct syscall_request*);
extern int syscall_request_publish_result(struct syscall_request*);
extern int f03_reply_observer_ignores_wire(struct syscall_request*,struct syscall_response*,struct thread*);
_Static_assert(_Generic(&syscall_request_copy_result,int(*)(struct syscall_request*,const struct syscall_request*):1,default:0),"exact copy helper type");
_Static_assert(_Generic(&syscall_offload_prepare_result,int(*)(struct syscall_request*,struct syscall_response*,int,int,unsigned long,int,unsigned long):1,default:0),"exact prepare helper type");
#endif
