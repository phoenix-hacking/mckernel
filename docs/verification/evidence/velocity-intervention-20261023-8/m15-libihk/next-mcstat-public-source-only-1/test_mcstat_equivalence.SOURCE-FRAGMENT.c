/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual original-C/Rust comparison body, source-only; no main or executable queue.
 * Future granted fixture links access/open/ioctl/close through these wrap consumers. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <ihk/ihk_host_user.h>
#include <ihk/ihk_rusage.h>
extern int ihk_os_get_num_numa_nodes(int),ref_ihk_os_get_num_numa_nodes(int);
extern int ihk_os_getrusage(int,struct ihk_os_rusage*,size_t),ref_ihk_os_getrusage(int,struct ihk_os_rusage*,size_t);
extern size_t ihklib_mcstat_rusage_size(void),ihklib_mcstat_rusage_threads_offset(void),ihklib_mcstat_request_size(void);
struct desc {struct ihk_os_rusage *rusage;size_t size_rusage;};
struct event {int kind,fd,mode;unsigned long command;uintptr_t output;size_t size;char path[64];};
static struct event events[8];static int ne;
static struct {int access_error,open_error,io_ret,io_errno,partial_write;} scenario;
static struct event *record(int kind){assert(ne<8);struct event *e=&events[ne++];memset(e,0,sizeof *e);e->kind=kind;return e;}
int __wrap_access(const char *path,int mode){struct event *e=record(1);e->mode=mode;strcpy(e->path,path);if(scenario.access_error){errno=EACCES;return -1;}return 0;}
int __wrap_open(const char *path,int mode,...){struct event *e=record(2);e->mode=mode;strcpy(e->path,path);if(scenario.open_error){errno=ENOENT;return -1;}return 17;}
int __wrap_close(int fd){struct event *e=record(4);e->fd=fd;errno=EBADF;return -1;}
int __wrap_ioctl(int fd,unsigned long request,...){
 struct event *e=record(3);e->fd=fd;e->command=request;
 if(request==IHK_OS_GETRUSAGE){va_list ap;va_start(ap,request);struct desc *d=va_arg(ap,struct desc*);va_end(ap);e->output=(uintptr_t)d->rusage;e->size=d->size_rusage;if(scenario.partial_write)memset(d->rusage,0x69,8);}
 else assert(request==IHK_OS_GET_NUM_NUMA_NODES);
 errno=scenario.io_errno;return scenario.io_ret;
}
static unsigned compare_case(int api,int null,size_t size){
 struct ihk_os_rusage buffer,initial,expected_output;memset(&initial,0xa5,sizeof initial);buffer=initial;ne=0;errno=0;
 int expected=api?ref_ihk_os_getrusage(-7,null?NULL:&buffer,size):ref_ihk_os_get_num_numa_nodes(-7);int expected_errno=errno;struct event expected_events[8];int expected_count=ne;memcpy(expected_events,events,sizeof events);expected_output=buffer;
 buffer=initial;ne=0;errno=0;int result=api?ihk_os_getrusage(-7,null?NULL:&buffer,size):ihk_os_get_num_numa_nodes(-7);
 assert(result==expected&&errno==expected_errno&&ne==expected_count);assert(memcmp(events,expected_events,(size_t)ne*sizeof events[0])==0);assert(memcmp(&buffer,&expected_output,sizeof buffer)==0);return 1;
}
unsigned test_mcstat_public_source_fragment(void){
 assert(ihklib_mcstat_rusage_size()==sizeof(struct ihk_os_rusage));assert(ihklib_mcstat_rusage_threads_offset()==offsetof(struct ihk_os_rusage,num_threads));assert(ihklib_mcstat_request_size()==sizeof(struct desc));
 size_t sizes[]={0,sizeof(struct ihk_os_rusage)-1,sizeof(struct ihk_os_rusage),sizeof(struct ihk_os_rusage)+1};int returns[]={-1,0,1,3};unsigned vectors=0;
 for(int api=0;api<2;api++)for(int null=0;null<2;null++)for(unsigned n=0;n<4;n++)for(int af=0;af<2;af++)for(int of=0;of<2;of++)for(unsigned rc=0;rc<4;rc++)for(int partial=0;partial<2;partial++){
  scenario=(typeof(scenario)){af,of,returns[rc],EIO,partial};vectors+=compare_case(api,null,sizes[n]);
 }
 return vectors;
}
