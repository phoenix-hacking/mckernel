#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#define EINVAL 22
#define SCD_MSG_EVENTFD 0x46
struct ihk_ikc_channel_desc {int unused;};
#include "actual_structs.c"
typedef int (*syscall_ikc_send_fn_t)(void *,void *,int);
static unsigned char capture[128];static int cpu,callcount,retvalue,optvalue;static uintptr_t channel;
struct cpulocal {struct ihk_ikc_channel_desc *ikc2linux;};
static struct cpulocal cl={.ikc2linux=(void *)0x1234};
static struct cpulocal *get_cpu_local_var(int n){cpu=n;return &cl;}
static int ihk_ikc_send(struct ihk_ikc_channel_desc *c,void *p,int o){channel=(uintptr_t)c;optvalue=o;callcount++;memcpy(capture,p,128);return retvalue;}
#include "actual_bodies.c"
int main(void){_Static_assert(sizeof(struct ikc_scd_packet)==128,"packet size");if(syscall_eventfd_packet_prepare_result(NULL,1,2)!=-22||syscall_eventfd_send_result(NULL,1,2,NULL)!=-22)return 2;int vals[]={0,-7,INT_MAX};int rets[]={0,-11,5};for(int i=0;i<3;i++)for(int j=0;j<3;j++){int v=vals[i],r=rets[j];retvalue=r;cpu=-1;channel=0;optvalue=-1;callcount=0;eventfd(v);printf("%d %d %d %lu %d %d ",v,r,cpu,(unsigned long)channel,optvalue,callcount);for(int k=0;k<128;k++)printf("%02x",capture[k]);puts("");}return 0;}
