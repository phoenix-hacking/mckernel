/* Source-routing observations only, never a real IHK/device/native provider. */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <ihk/ihklib.h>
struct Event { int op,index; };
static struct Event events[16];
static int used,fault,target,live;
static void *allocation;
static void event(int op,int index) { assert(used<16); events[used++]=(struct Event){op,index}; }
void *observation_calloc(size_t n,size_t size) { assert(!allocation); allocation=calloc(n,size); assert(allocation); ++live; return allocation; }
void observation_free(void *p) { if(p) { assert(p==allocation&&live==1); allocation=NULL; --live; } free(p); }
int observation_reserved_cpu_count(int device) { event(1,device); return device!=0?-ENODEV:fault==1?-31:1; }
int observation_query_cpu(int device,int *cpus,int count) { event(2,device); assert(count==1&&cpus); if(device!=0)return -ENODEV; if(fault==2)return -32; cpus[0]=2; return 0; }
int observation_assign_cpu(int os,int *cpus,int count) { event(3,os); assert(os==target&&count==1&&cpus[0]==2); return fault==3?-33:0; }
int observation_release_cpu(int device,int *cpus,int count) { (void)cpus;(void)count;event(7,device);return -99; }
int observation_reserved_mem_count(int device) { event(4,device); return device!=0?-ENODEV:fault==4?-34:1; }
int observation_query_mem(int device,struct ihk_mem_chunk *chunks,int count) { event(5,device);assert(count==1&&chunks);if(device!=0)return -ENODEV;if(fault==5)return -35;chunks[0]=(struct ihk_mem_chunk){4096,0};return 0; }
int observation_assign_mem(int os,struct ihk_mem_chunk *chunks,int count) { event(6,os);assert(os==target&&count==1&&chunks[0].size==4096&&chunks[0].numa_node_number==0);return fault==6?-36:0; }
static void reset(int os,int failed) { assert(!live&&!allocation);used=0;fault=failed;target=os; }
static void expect(int result,int expected,int start,int length,int baseline) { assert(result==expected&&live==0&&!allocation);assert(used==length);for(int i=0;i<length;i++){int op=start+i;assert(events[i].op==op);int index=op==3||op==6?target:0;if(baseline&&op==1)index=target;if(baseline&&op==5)index=target;assert(events[i].index==index);} }
typedef int (*Route)(int device,int os);
int observation_run(int baseline,Route phase,Route memory) {
 if(baseline) { reset(1,0);expect(phase(0,1),-ENODEV,1,1,1);reset(1,0);expect(memory(0,1),-ENODEV,4,2,1);puts("baseline routing checks=2 wrong-device-indices-observed");return 0; }
 reset(1,0);expect(phase(0,1),0,1,6,0);
 for(int i=1;i<=6;i++){reset(1,i);expect(phase(0,1),-30-i,1,i,0);}
 reset(0,0);expect(phase(0,0),0,1,6,0);
 reset(1,0);expect(memory(0,1),0,4,3,0);
 puts("candidate routing checks=9 device-count-query=0 assign-os=1 default0-0-preserved");return 0;
}
