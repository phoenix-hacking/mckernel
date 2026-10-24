/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact original C request/admission body versus actual new Rust entry.
 * Host syscall/allocation/publication are controlled callbacks: no native credit.
 */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "SyscallRequest.ACTUAL-C-ABI.inc"
#define IHK_DMA_ALIGN
_Static_assert(sizeof(int)==4 && sizeof(long)==8 && sizeof(unsigned long)==8,"supported LP64");
_Static_assert(sizeof(struct syscall_request)==72 && _Alignof(struct syscall_request)==8,"exact supported request extent/alignment");
_Static_assert(__builtin_offsetof(struct syscall_request,rtid)==0 && __builtin_offsetof(struct syscall_request,ttid)==4 && __builtin_offsetof(struct syscall_request,valid)==8 && __builtin_offsetof(struct syscall_request,number)==16 && __builtin_offsetof(struct syscall_request,args)==24,"actual request fields");
static struct trace {int used;int events[8];unsigned char request[72];int cpu,fd,create;unsigned long mask;} trace;
static int cpu_value,nr_value,flags_value,copy_error;static long host_result,publish_result;
static void event(int e){assert(trace.used<8);trace.events[trace.used++]=e;}
int ihk_mc_get_processor_id(void){event(1);return cpu_value;}
long do_syscall(struct syscall_request *request,int cpu)
{
    struct syscall_request expected;memset(&expected,0,sizeof expected);expected.number=(unsigned long)nr_value;expected.args[1]=(unsigned long)flags_value;
    event(2);assert(cpu==cpu_value && (uintptr_t)request%_Alignof(struct syscall_request)==0);assert(!memcmp(request,&expected,sizeof expected));
    memcpy(trace.request,request,sizeof *request);trace.cpu=cpu;
    request->valid=ULONG_MAX;request->args[5]=ULONG_MAX;return host_result;
}
#define syscall_signalfd_create_bridge original_syscall_signalfd_create_bridge
#include "original_create.ACTUAL-C-BODY.inc"
#undef syscall_signalfd_create_bridge
extern long syscall_signalfd_create_bridge(int,int);
typedef long (*copy_fn_t)(unsigned char*,unsigned long,size_t);
typedef long (*create_fn_t)(int,int);
typedef long (*publish_fn_t)(void*,int,const unsigned long*,int);
extern long signalfd4_body_result(int,unsigned long,size_t,size_t,int,void*,int,copy_fn_t,create_fn_t,publish_fn_t);
static long copy_mask(unsigned char *dst,unsigned long src,size_t bytes)
{event(3);assert(bytes==8);if(copy_error)return -1;memcpy(dst,(const void*)src,bytes);return 0;}
static long publish(void *thread,int fd,const unsigned long *mask,int create)
{event(4);assert(thread==(void*)0x1234);trace.fd=fd;trace.mask=*mask;trace.create=create;return publish_result;}
static long direct_pair(int nr,int flags,int cpu,long result)
{
    nr_value=nr;flags_value=flags;cpu_value=cpu;host_result=result;memset(&trace,0,sizeof trace);
    long c=original_syscall_signalfd_create_bridge(nr,flags);struct trace original=trace;memset(&trace,0,sizeof trace);
    long rust=syscall_signalfd_create_bridge(nr,flags);
    assert(c==result && rust==c && !memcmp(&trace,&original,sizeof trace));assert(trace.used==2 && trace.events[0]==1 && trace.events[1]==2);return rust;
}
static long helper_pair(int fd,unsigned long *mask,size_t size,int flags,void *thread)
{
    nr_value=289;flags_value=flags;memset(&trace,0,sizeof trace);
    long c=signalfd4_body_result(fd,(unsigned long)mask,size,8,flags,thread,289,copy_mask,original_syscall_signalfd_create_bridge,publish);struct trace original=trace;memset(&trace,0,sizeof trace);
    long rust=signalfd4_body_result(fd,(unsigned long)mask,size,8,flags,thread,289,copy_mask,syscall_signalfd_create_bridge,publish);
    assert(c==rust && !memcmp(&trace,&original,sizeof trace));return rust;
}
int main(void)
{
    const int nrs[]={INT_MIN,-1,0,1,289,INT_MAX},flags[]={INT_MIN,-1,0,1,04000,02000000,02004000,INT_MAX},cpus[]={INT_MIN,-1,0,1,3,INT_MAX};
    const long results[]={LONG_MIN,-12,-22,-38,-1,0,1,37,(long)INT_MAX+1,LONG_MAX};
    unsigned direct=0,create_cases=0,existing_cases=0,frontend=0,publish_ENOMEM_after_hostFD=0;
    for(unsigned i=0;i<6;i++)for(unsigned j=0;j<8;j++)for(unsigned k=0;k<6;k++)for(unsigned l=0;l<10;l++){direct_pair(nrs[i],flags[j],cpus[k],results[l]);direct++;}
    const int valid_flags[]={0,04000,02000000,02004000},existing_fds[]={INT_MIN,-2,0,37};const unsigned long masks[]={0,1,1UL<<63,ULONG_MAX};const long publications[]={-12,-22,0,37,LONG_MAX};
    copy_error=0;cpu_value=3;
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<4;j++)for(unsigned k=0;k<10;k++)for(unsigned l=0;l<5;l++){
        unsigned long mask=masks[j];host_result=results[k];publish_result=publications[l];long got=helper_pair(-1,&mask,8,valid_flags[i],(void*)0x1234);
        if(host_result<0){assert(got==host_result && trace.used==3 && trace.events[0]==3 && trace.events[1]==1 && trace.events[2]==2);}
        else {assert(got==publish_result && trace.used==4 && trace.events[3]==4 && trace.fd==(int)host_result && trace.mask==mask && trace.create==1);if(publish_result==-12)publish_ENOMEM_after_hostFD++;}
        create_cases++;
    }
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<4;j++)for(unsigned k=0;k<4;k++)for(unsigned l=0;l<5;l++){
        unsigned long mask=masks[j];host_result=-38;publish_result=publications[l];long got=helper_pair(existing_fds[k],&mask,8,valid_flags[i],(void*)0x1234);
        assert(got==publish_result && trace.used==2 && trace.events[0]==3 && trace.events[1]==4 && trace.fd==existing_fds[k] && trace.mask==mask && trace.create==0);existing_cases++;
    }
    for(int i=0;i<5;i++){
        unsigned long mask=ULONG_MAX;copy_error=i==2;host_result=37;publish_result=37;long got=helper_pair(-1,i==1?NULL:&mask,i==0?7:8,i==3?1:0,i==4?NULL:(void*)0x1234);
        assert(got==(i==1 || i==2?-14:-22));assert(trace.used==(i>=2?1:0));if(trace.used)assert(trace.events[0]==3);frontend++;
    }
    assert(direct==2880 && create_cases==800 && existing_cases==320 && frontend==5 && publish_ENOMEM_after_hostFD==80);
    printf("PASS_SIGNALFD_CREATE_ACTUAL_C_RUST direct=%u unchanged_helper_create=%u existing_fd=%u frontend_errors=%u hostFD_then_publish_ENOMEM=%u request_bytes=72 natural_align=8 order_exact=1 controlled_only=1\n",direct,create_cases,existing_cases,frontend,publish_ENOMEM_after_hostFD);
    return 0;
}
