/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * No real device/syscall effects: access/open/ioctl/close are exact controlled consumers. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <ihk/ihk_host_user.h>
#include <ihk/ihk_rusage.h>
extern int ihk_reserve_cpu(int,int*,int), ihk_release_cpu(int,int*,int);
extern int ihk_query_cpu(int,int*,int), ihk_get_num_reserved_cpus(int);
extern int ref_ihk_reserve_cpu(int,int*,int), ref_ihk_release_cpu(int,int*,int);
extern int ref_ihk_query_cpu(int,int*,int), ref_ihk_get_num_reserved_cpus(int);
extern size_t ihklib_cpu_req_size(void),ihklib_cpu_req_alignment(void),ihklib_cpu_req_count_offset(void);
struct event {int kind,fd,mode,count;unsigned long command;int *cpus;char path[64];};
struct scenario {int access_fail,open_fail,get_rc,change_rc,io_errno,close_errno;};
static struct scenario s;
static struct event events[8];static int ne,accesses;
static struct event *add(int kind) {assert(ne<8);struct event *p=&events[ne++];memset(p,0,sizeof *p);p->kind=kind;return p;}
int access(const char *path,int mode) {struct event *p=add(1);p->mode=mode;strcpy(p->path,path);accesses++;if(s.access_fail==accesses){errno=EACCES;return -1;}return 0;}
int open(const char *path,int flags,...) {struct event *p=add(2);p->mode=flags;strcpy(p->path,path);if(s.open_fail){errno=ENOENT;return -1;}return 17;}
int close(int fd) {struct event *p=add(4);p->fd=fd;errno=s.close_errno;return -1;}
int ioctl(int fd,unsigned long command,...) {
 struct event *p=add(3);p->fd=fd;p->command=command;errno=s.io_errno;
 if(command==IHK_DEVICE_GET_NUM_CPUS)return s.get_rc;
 assert(command==IHK_DEVICE_RESERVE_CPU||command==IHK_DEVICE_RELEASE_CPU||command==IHK_DEVICE_QUERY_CPU);
 va_list ap;va_start(ap,command);struct ihk_cpu_req *req=va_arg(ap,struct ihk_cpu_req*);va_end(ap);
 p->count=req->num_cpus;p->cpus=req->cpus;
 if(command==IHK_DEVICE_QUERY_CPU&&s.change_rc==0)for(int i=0;i<req->num_cpus;i++)req->cpus[i]=91-i;
 return s.change_rc;
}
static int run(int rust,int api,int index,int *cpus,int count) {
 if(api==0)return rust?ihk_reserve_cpu(index,cpus,count):ref_ihk_reserve_cpu(index,cpus,count);
 if(api==1)return rust?ihk_release_cpu(index,cpus,count):ref_ihk_release_cpu(index,cpus,count);
 if(api==2)return rust?ihk_query_cpu(index,cpus,count):ref_ihk_query_cpu(index,cpus,count);
 return rust?ihk_get_num_reserved_cpus(index):ref_ihk_get_num_reserved_cpus(index);
}
int main(void) {
 assert(ihklib_cpu_req_size()==sizeof(struct ihk_cpu_req));assert(ihklib_cpu_req_alignment()==_Alignof(struct ihk_cpu_req));assert(ihklib_cpu_req_count_offset()==offsetof(struct ihk_cpu_req,num_cpus));
 int counts[]={-1,0,1,3,1024,1025};int returns[]={-1,0,1,3};unsigned cases=0;
 for(int api=0;api<4;api++)for(unsigned c=0;c<6;c++)for(int null=0;null<2;null++)for(int af=0;af<3;af++)for(int of=0;of<2;of++)for(unsigned gr=0;gr<4;gr++)for(unsigned cr=0;cr<4;cr++) {
  s=(struct scenario){af,of,returns[gr],returns[cr],EIO,EBADF};
  int array[1024],before[1024],after[1024];for(int i=0;i<1024;i++)before[i]=i*2;memcpy(array,before,sizeof array);
  ne=accesses=0;errno=0;int expected=run(0,api,-7,null?NULL:array,counts[c]);int expected_errno=errno;int expected_ne=ne;struct event expected_events[8];memcpy(expected_events,events,sizeof events);memcpy(after,array,sizeof array);
  ne=accesses=0;errno=0;memcpy(array,before,sizeof array);int actual=run(1,api,-7,null?NULL:array,counts[c]);
  assert(actual==expected&&errno==expected_errno&&ne==expected_ne);assert(memcmp(events,expected_events,(size_t)ne*sizeof events[0])==0);assert(memcmp(array,after,sizeof array)==0);cases++;
 }
 printf("PASS %u actual C/Rust public CPU equivalence vectors, actual UAPI layout, ordered ioctl/access/open/close, return/errno/output preservation\n",cases);return 0;
}
