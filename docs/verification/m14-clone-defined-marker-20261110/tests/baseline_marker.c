/* Expected compile failure only. Never execute an uninitialized marker read. */
#include "wire_types.h"
unsigned long baseline_legacy_marker(int clone_flags,int ppid_parent_pid,
    unsigned long user_start,unsigned long user_length,unsigned long root_pa)
{
	struct syscall_request request1 IHK_DMA_ALIGN;
    request1.number=__NR_clone;
    request1.args[0]=clone_host_parent_flags_result(clone_flags,ppid_parent_pid);
    request1.args[1]=user_start;
    request1.args[2]=user_length;
    request1.args[3]=root_pa;
    /* Same typed slot consumed by the current nr56 reply discriminator. */
    return request1.args[5];
}
