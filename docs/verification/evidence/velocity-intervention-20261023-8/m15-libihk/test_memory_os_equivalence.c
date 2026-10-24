/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Controlled host consumers only: no real directory/device/ioctl effects. */
#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "selected_memory_layout.h"
extern int ihk_reserve_mem(int,struct ihk_mem_chunk*,int),ihk_release_mem(int,struct ihk_mem_chunk*,int),ihk_query_mem(int,struct ihk_mem_chunk*,int),ihk_get_num_reserved_mem_chunks(int);
extern int ref_ihk_reserve_mem(int,struct ihk_mem_chunk*,int),ref_ihk_release_mem(int,struct ihk_mem_chunk*,int),ref_ihk_query_mem(int,struct ihk_mem_chunk*,int),ref_ihk_get_num_reserved_mem_chunks(int);
extern int ihk_get_num_os_instances(int),ihk_get_os_instances(int,int*,int),ref_ihk_get_num_os_instances(int),ref_ihk_get_os_instances(int,int*,int);
struct ihklib_reserve_mem_conf reserve_mem_conf;
int loglevel=1;
static struct {int access_fail,open_fail,io_fail,alloc_fail,count,uid,dir_fail,io_rc;} s;
struct event {int kind;long long a,b,c;unsigned long sizes[4];int nodes[4];int config[3];char text[96];};
static struct event events[128];static int ne,access_n,open_n,io_n,alloc_n,dir_n,dir_pos;
struct allocation {void *p;int live;};static struct allocation allocations[32];static int na;
static struct event *ev(int k) {assert(ne<128);struct event *e=&events[ne++];memset(e,0,sizeof *e);e->kind=k;return e;}
void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_calloc(size_t n,size_t z) {struct event *e=ev(5);e->a=(long long)n;e->b=(long long)z;alloc_n++;if(alloc_n==s.alloc_fail||n>4096||z>64){errno=ENOMEM;return NULL;}assert(na<32);void *p=__real_calloc(n,z);assert(p);allocations[na]=(struct allocation){p,1};e->c=++na;return p;}
void __wrap_free(void *p) {struct event *e=ev(6);if(!p)return;for(int i=0;i<na;i++)if(allocations[i].p==p&&allocations[i].live){allocations[i].live=0;e->a=i+1;__real_free(p);return;}assert(!"unknown/double free");}
int access(const char *p,int mode) {struct event *e=ev(1);e->a=mode;snprintf(e->text,sizeof e->text,"%s",p);if(++access_n==s.access_fail){errno=EACCES;return -1;}return 0;}
int open(const char *p,int flags,...) {struct event *e=ev(2);e->a=flags;snprintf(e->text,sizeof e->text,"%s",p);if(++open_n==s.open_fail){errno=ENOENT;return -1;}return flags==O_WRONLY?29:17;}
int close(int fd) {struct event *e=ev(4);e->a=fd;errno=EBADF;return -1;}
ssize_t write(int fd,const void *b,size_t n) {struct event *e=ev(7);e->a=fd;e->b=n;size_t take=n<sizeof e->text?n:sizeof e->text;memcpy(e->text,b,take);return (ssize_t)n;}
uid_t geteuid(void) {ev(8);return (uid_t)s.uid;}
int ioctl(int fd,unsigned long command,...) {
 struct event *e=ev(3);e->a=fd;e->b=command;io_n++;
 va_list ap;va_start(ap,command);struct ihk_mem_req *r=va_arg(ap,struct ihk_mem_req*);va_end(ap);
 assert(command==IHK_DEVICE_RESERVE_MEM||command==IHK_DEVICE_RELEASE_MEM||command==IHK_DEVICE_QUERY_MEM||command==IHK_DEVICE_RELEASE_MEM_PARTIALLY);
 e->c=r->num_chunks;e->config[0]=r->min_chunk_size;e->config[1]=r->max_size_ratio_all;e->config[2]=r->timeout;
 for(int i=0;i<r->num_chunks&&i<4;i++){e->sizes[i]=r->sizes[i];e->nodes[i]=r->numa_ids[i];}
 if(io_n==s.io_fail){errno=EIO;return s.io_rc;}
 if(command==IHK_DEVICE_QUERY_MEM){if(r->num_chunks==0)r->num_chunks=s.count;else for(int i=0;i<r->num_chunks;i++){r->sizes[i]=(i==0?64UL:256UL)<<20;r->numa_ids[i]=i;}}
 return 0;
}
static const char *names[]={".","mcos7","mcos02","mcostext","mcos-1","mcos","other"};static struct dirent entry;
DIR *opendir(const char *p) {struct event *e=ev(9);snprintf(e->text,sizeof e->text,"%s",p);if(++dir_n==s.dir_fail){errno=ENOENT;return NULL;}dir_pos=0;return (DIR*)&entry;}
struct dirent *readdir(DIR *p) {assert(p==(DIR*)&entry);ev(10);if(dir_pos==7)return NULL;memset(&entry,0,sizeof entry);strcpy(entry.d_name,names[dir_pos++]);return &entry;}
int closedir(DIR *p) {assert(p==(DIR*)&entry);ev(11);errno=EBADF;return -1;}
static void reset(void) {ne=access_n=open_n=io_n=alloc_n=dir_n=dir_pos=na=0;memset(allocations,0,sizeof allocations);errno=0;}
static unsigned live_mask(void) {unsigned m=0;for(int i=0;i<na;i++)if(allocations[i].live)m|=1u<<i;return m;}
static void harness_retire_allocations(void) {for(int i=0;i<na;i++)if(allocations[i].live)__real_free(allocations[i].p);}
static int memory_call(int rust,int api,struct ihk_mem_chunk *p,int n) {switch(api){case 0:return rust?ihk_reserve_mem(-3,p,n):ref_ihk_reserve_mem(-3,p,n);case 1:return rust?ihk_release_mem(-3,p,n):ref_ihk_release_mem(-3,p,n);case 2:return rust?ihk_query_mem(-3,p,n):ref_ihk_query_mem(-3,p,n);default:return rust?ihk_get_num_reserved_mem_chunks(-3):ref_ihk_get_num_reserved_mem_chunks(-3);}}
static unsigned cases;
static void memory_vector(int api,int n,int null,int all,int balanced) {
 struct ihk_mem_chunk initial[4],data[4],after[4];memset(initial,0xa5,sizeof initial);for(int i=0;i<4;i++){initial[i].size=64UL<<20;initial[i].numa_node_number=i;}if(all)initial[0].size=~0UL;
 struct ihklib_reserve_mem_conf conf={balanced,0,0,4096,98,30};reserve_mem_conf=ref_reserve_mem_conf=conf;
 reset();memcpy(data,initial,sizeof data);int want=memory_call(0,api,null?NULL:data,n);int want_errno=errno;struct event expected[128];int expected_n=ne;memcpy(expected,events,sizeof events);memcpy(after,data,sizeof data);unsigned leaks=live_mask();struct ihklib_reserve_mem_conf post=ref_reserve_mem_conf;harness_retire_allocations();
 reset();memcpy(data,initial,sizeof data);int got=memory_call(1,api,null?NULL:data,n);
 assert(got==want&&errno==want_errno&&ne==expected_n);assert(memcmp(events,expected,(size_t)ne*sizeof events[0])==0);assert(memcmp(data,after,sizeof data)==0);assert(live_mask()==leaks);assert(memcmp(&reserve_mem_conf,&post,sizeof post)==0);harness_retire_allocations();cases++;
}
static void os_vector(int api,int requested,int null) {
 int indices[8],initial[8],after[8];for(int i=0;i<8;i++)initial[i]=0x55555555;
 reset();memcpy(indices,initial,sizeof indices);int want=api?ref_ihk_get_os_instances(2,null?NULL:indices,requested):ref_ihk_get_num_os_instances(2);int want_errno=errno;struct event expected[128];int expected_n=ne;memcpy(expected,events,sizeof events);memcpy(after,indices,sizeof indices);
 reset();memcpy(indices,initial,sizeof indices);int got=api?ihk_get_os_instances(2,null?NULL:indices,requested):ihk_get_num_os_instances(2);
 assert(got==want&&errno==want_errno&&ne==expected_n);assert(memcmp(events,expected,(size_t)ne*sizeof events[0])==0);assert(memcmp(indices,after,sizeof indices)==0);cases++;
}
int main(void) {
 _Static_assert(sizeof(struct ihk_mem_chunk)==16,"LP64 public chunk");_Static_assert(offsetof(struct ihk_mem_chunk,numa_node_number)==8,"node offset");_Static_assert(sizeof(struct ihk_mem_req)==32,"memory request size");_Static_assert(offsetof(struct dirent,d_name)==19,"selected glibc dirent");
 /* Valid provider replies; malformed replies that make original C undefined are excluded. */
 int counts[]={-1,0,1,2,2049};
 for(int api=0;api<4;api++)for(int n=0;n<5;n++)for(int null=0;null<2;null++)for(int fail=0;fail<12;fail++){
  s=(typeof(s)){.count=2,.uid=0,.io_rc=-1};
  if(fail==1)s.access_fail=1;if(fail==2)s.access_fail=2;if(fail==3)s.open_fail=1;if(fail>=4&&fail<=7)s.alloc_fail=fail-3;if(fail>=8)s.io_fail=fail-7;
  memory_vector(api,counts[n],null,0,0);
 }
 for(int api=0;api<3;api++)for(int fail=0;fail<15;fail++){
  s=(typeof(s)){.count=2,.uid=0,.io_rc=-1};if(fail<=7)s.alloc_fail=fail;else s.io_fail=fail-7;
  memory_vector(api,2,0,api==1,api==0);
 }
 /* Count-zero and negative count replies, syscall positive-nonzero errors. */
 for(int c=-1;c<=0;c++)for(int api=1;api<4;api++){s=(typeof(s)){.count=c,.uid=1000,.io_rc=-1};memory_vector(api,2,0,api==1,0);}
 for(int api=0;api<4;api++){s=(typeof(s)){.count=2,.uid=1000,.io_fail=1,.io_rc=1};memory_vector(api,2,0,0,0);}
 int requested[]={-1,0,4,5,6};
 for(int api=0;api<2;api++)for(int n=0;n<5;n++)for(int null=0;null<2;null++)for(int uid=0;uid<2;uid++)for(int df=0;df<3;df++){
  s=(typeof(s)){.uid=uid?1000:0,.dir_fail=df};os_vector(api,requested[n],null);
 }
 printf("PASS %u actual original-C/Rust memory+OS vectors; ABI/order/errno/output/allocation-lifetime parity only\n",cases);return 0;
}
