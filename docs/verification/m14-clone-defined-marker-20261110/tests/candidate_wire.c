/* One sequential changed-input protocol regression. No syscall/fork/IKC/native
 * operation is invoked. Actual initializer, C wire types, unchanged Rust helpers
 * and exact observer discriminator are joined at the C/Rust ABI boundary. */
#include "wire_types.h"
#include <stdio.h>
#include <string.h>
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c); return 1; } } while (0)
int main(void)
{
	struct syscall_request request1 IHK_DMA_ALIGN = { 0 };
    struct syscall_request zero={0};
    struct syscall_request packet={0};
    struct syscall_response response={0};
    _Alignas(64) unsigned char thread_token[5568]={0};
    struct thread *thread=(struct thread*)(void*)thread_token;
    const unsigned long marker=UINT64_C(0x313030434b46434d);
    const unsigned long start=UINT64_C(0x100000000);
    const unsigned long length=UINT64_C(0x80000000);
    const unsigned long root=UINT64_C(0x23456000);
    const int clone_flags=0x00008000|17;
    const int parent_pid=88;
    const int tid=321;
    CHECK(memcmp(&request1,&zero,sizeof(request1))==0);
    /* Concrete protocol values represent the original known VM/root inputs.
     * The real unchanged parent-flags helper is called, never stubbed.
     * The patch byte comparison separately proves every actual VM/physical
     * expression, later field assignment and branch is unchanged. */
    request1.number=__NR_clone;
    request1.args[0]=clone_host_parent_flags_result(clone_flags,parent_pid);
    request1.args[1]=start;
    request1.args[2]=length;
    request1.args[3]=root;
    CHECK(request1.args[0]==(unsigned long)clone_flags);
    CHECK(request1.args[1]==start && request1.args[2]==length && request1.args[3]==root);
    CHECK(request1.args[4]==0 && request1.args[5]==0);
    CHECK(syscall_offload_prepare_result(&request1,&response,tid,(int)request1.number,request1.args[0],203,0)==0);
    CHECK(request1.rtid==tid && request1.ttid==0 && response.req_thread_status==0 && response.pde_data==NULL);
    CHECK(syscall_send_prepare_result(&request1,&response)==0);
    CHECK(syscall_request_copy_result(&packet,&request1)==0);
    CHECK(syscall_request_publish_result(&packet)==0);
    CHECK(request1.valid==0 && packet.valid==1);
    CHECK(memcmp(request1.args,packet.args,sizeof(packet.args))==0);
    CHECK(packet.number==__NR_clone && packet.rtid==tid && packet.ttid==0);
    CHECK(f03_reply_observer_ignores_wire(&request1,&response,thread)==1);
    CHECK(f03_reply_observer_ignores_wire(&packet,&response,thread)==1);
    /* Existing selector1/report producer reuses the same request. */
    request1.number=__NR_clone;
    request1.args[0]=1;
    request1.args[1]=859;
    CHECK(request1.args[0]==1 && request1.args[1]==859);
    CHECK(request1.args[2]==length && request1.args[3]==root);
    CHECK(request1.args[4]==0 && request1.args[5]==0);
    CHECK(f03_reply_observer_ignores_wire(&request1,&response,thread)==1);
    /* Exact marker is discriminated; this is not control/ACK success. */
    packet=request1;
    packet.args[5]=marker;
    CHECK(f03_reply_observer_ignores_wire(&packet,&response,thread)==0);
    CHECK(request1.args[5]==0 && packet.args[0]==1 && packet.args[1]==859);
    packet.args[5]=marker^1;
    CHECK(f03_reply_observer_ignores_wire(&packet,&response,thread)==1);
    /* Existing failed-report cleanup request remains a real kill wire shape;
     * no kill operation, host proxy, current task or signal is run here. */
    request1.number=__NR_kill;
    request1.args[0]=859;
    request1.args[1]=9;
    CHECK(request1.number==__NR_kill && request1.args[0]==859 && request1.args[1]==9);
    CHECK(request1.args[2]==length && request1.args[3]==root);
    CHECK(request1.args[4]==0 && request1.args[5]==0);
    CHECK(f03_reply_observer_ignores_wire(&request1,&response,thread)==1);
    puts("{\"status\":\"PASS\",\"case\":\"legacy-clone-defined-marker-and-known-wire-fields\",\"real_helpers\":true,\"legacy_marker_ignored\":true,\"exact_marker_discriminated_only\":true,\"known_args_preserved\":true,\"native_execution\":false}");
    return 0;
}
