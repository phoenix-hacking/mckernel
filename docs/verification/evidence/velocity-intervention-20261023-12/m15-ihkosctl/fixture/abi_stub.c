/* TEST ONLY: no production device/library behavior is supplied by this file.
 * Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <ihk/ihklib.h>
_Static_assert(sizeof(struct ihk_cpu_req)==16,"CPU ABI");
_Static_assert(sizeof(struct ihk_mem_req)==32,"MEM ABI");
_Static_assert(sizeof(struct ihk_ikc_req)==24,"IKC ABI");
_Static_assert(offsetof(struct ihk_ikc_req,num_cpus)==16,"IKC count ABI");
const char *ihklib_os_query_mem_type_str[]={"MemTotal","MemFree"};
static long setting(const char *key,long value){const char *p=getenv(key);return p?strtol(p,NULL,0):value;}
static void trace(const char *format,...){
 const char *path=getenv("IHKOS_FIXTURE_TRACE");if(!path)abort();FILE *out=fopen(path,"a");if(!out)abort();
 va_list ap;va_start(ap,format);vfprintf(out,format,ap);va_end(ap);fputc('\n',out);fclose(out);
}
int __wrap_open(const char *path,int flags,...){trace("open %s flags=%d",path,flags);if(setting("IHKOS_FAIL_OPEN",0)){errno=ENOENT;return -1;}return 17;}
int __wrap_close(int fd){trace("close %d",fd);return 0;}
int __wrap_ioctl(int fd,unsigned long request,...){
 trace("ioctl fd=%d request=%lx",fd,request);va_list ap;va_start(ap,request);
 if(setting("IHKOS_FAIL_REQUEST",-1)==(long)request){va_end(ap);errno=setting("IHKOS_ERRNO",EIO);return -1;}
 int ret=setting("IHKOS_IOCTL_RET",0);
 if(request==IHK_OS_GET_NUM_CPUS){va_end(ap);return ret?ret:setting("IHKOS_CPU_COUNT",3);}
 if(request==IHK_OS_LOAD||request==IHK_OS_SET_KARGS){trace("string=%s",(char *)va_arg(ap,uintptr_t));}
 else if(request==IHK_OS_BOOT||request==IHK_OS_SHUTDOWN||request==IHK_OS_CLEAR_KMSG||request==IHK_OS_ALLOC_CPU||request==IHK_OS_DEBUG_START){trace("integer=%d",va_arg(ap,int));}
 else if(request==IHK_OS_ALLOC_MEM){trace("size=%lu",va_arg(ap,unsigned long));}
 else if(request==IHK_OS_RESERVE_CPU){int *q=(int *)va_arg(ap,uintptr_t);trace("legacy_cpu count=%d",q[0]);for(int i=0;i<q[0];i++)trace("cpu[%d]=%d",i,q[i+1]);}
 else if(request==IHK_OS_RESERVE_MEM){unsigned long *q=(void *)va_arg(ap,uintptr_t);trace("legacy_mem start=%lx size=%lx",q[0],q[1]);}
 else if(request==IHK_OS_GET_BUILDID){char *q=va_arg(ap,char *);if(!ret){if(setting("IHKOS_BUILDID_NO_NUL",0))memset(q,'x',sizeof("fixture-build"));else strcpy(q,"fixture-build");}}
 else if(request==IHK_OS_QUERY_CPU||request==IHK_OS_ASSIGN_CPU||request==IHK_OS_RELEASE_CPU){
  struct ihk_cpu_req *q=va_arg(ap,struct ihk_cpu_req *);trace("cpu_req count=%d",q->num_cpus);
  if(request==IHK_OS_QUERY_CPU){if(!ret)for(int i=0;i<q->num_cpus;i++)q->cpus[i]=i;}
  else for(int i=0;i<q->num_cpus;i++)trace("cpu[%d]=%d",i,q->cpus[i]);
 }
 else if(request==IHK_OS_QUERY_MEM||request==IHK_OS_ASSIGN_MEM||request==IHK_OS_RELEASE_MEM){
  struct ihk_mem_req *q=va_arg(ap,struct ihk_mem_req *);trace("mem_req count=%d sizes=%d nodes=%d min=%d ratio=%d timeout=%d",q->num_chunks,!!q->sizes,!!q->numa_ids,q->min_chunk_size,q->max_size_ratio_all,q->timeout);
  if(request==IHK_OS_QUERY_MEM){if(!ret){if(!q->sizes)q->num_chunks=setting("IHKOS_MEM_COUNT",2);else for(int i=0;i<q->num_chunks;i++){q->sizes[i]=4096UL<<i;q->numa_ids[i]=i;}}}
  else for(int i=0;i<q->num_chunks;i++)trace("mem[%d]=%zu@%d",i,q->sizes[i],q->numa_ids[i]);
 }
 else if(request==IHK_OS_GET_IKC_MAP||request==IHK_OS_SET_IKC_MAP){
  struct ihk_ikc_req *q=va_arg(ap,struct ihk_ikc_req *);trace("ikc_req capacity=%d",q->num_cpus);
  if(request==IHK_OS_GET_IKC_MAP){if(!ret){q->num_cpus=3;for(int i=0;i<3;i++){q->src_cpus[i]=i*2;q->dst_cpus[i]=(i==1)?1:2;}}}
  else for(int i=0;i<q->num_cpus;i++)trace("ikc[%d]=%d:%d",i,q->src_cpus[i],q->dst_cpus[i]);
 }
 else trace("raw=%lx",va_arg(ap,unsigned long));
 va_end(ap);if(ret<0)errno=setting("IHKOS_ERRNO",EIO);return ret;
}
int ihk_os_get_status(int index){trace("ihk_os_get_status index=%d",index);return setting("IHKOS_STATUS",2);}
int ihk_os_kmsg(int index,char *out,ssize_t size){
 trace("ihk_os_kmsg index=%d capacity=%zd",index,size);const char *message="fixture kmsg";memcpy(out,message,strlen(message));
 return setting("IHKOS_KMSG_RET",strlen(message));
}
int ihk_os_makedumpfile(int index,char *path,int level,int interactive){trace("ihk_os_makedumpfile index=%d path=%s level=%d interactive=%d",index,path,level,interactive);return setting("IHKOS_LIB_RET",0);}
int ihklib_os_query_mem_sysfs(int index,char *out,ssize_t size,const char *kind){trace("ihklib_os_query_mem_sysfs index=%d capacity=%zd kind=%s",index,size,kind);snprintf(out,size,"4096@0,8192@1");return setting("IHKOS_LIB_RET",0);}
time_t __wrap_time(time_t *out){trace("time");if(setting("IHKOS_FAIL_TIME",0)){errno=EIO;return (time_t)-1;}time_t t=1700000000;if(out)*out=t;return t;}
struct tm *__real_localtime(const time_t *);
struct tm *__wrap_localtime(const time_t *value){trace("localtime %ld",(long)*value);if(setting("IHKOS_FAIL_LOCALTIME",0)){errno=EOVERFLOW;return NULL;}return __real_localtime(value);}
size_t __real_strftime(char *,size_t,const char *,const struct tm *);
size_t __wrap_strftime(char *out,size_t size,const char *fmt,const struct tm *tm){trace("strftime size=%zu format=%s",size,fmt);if(setting("IHKOS_FAIL_STRFTIME",0)){errno=EIO;return 0;}return __real_strftime(out,size,fmt,tm);}
void *__real_calloc(size_t,size_t);void *__real_malloc(size_t);char *__real_strdup(const char *);
static int calloc_calls,malloc_calls,strdup_calls;
void *__wrap_calloc(size_t n,size_t size){if(++calloc_calls==setting("IHKOS_FAIL_CALLOC",-1)||(size&&n>8388608/size)){errno=ENOMEM;return NULL;}return __real_calloc(n,size);}
void *__wrap_malloc(size_t size){if(++malloc_calls==setting("IHKOS_FAIL_MALLOC",-1)||size>8388608){errno=ENOMEM;return NULL;}return __real_malloc(size);}
char *__wrap_strdup(const char *s){if(++strdup_calls==setting("IHKOS_FAIL_STRDUP",-1)){errno=ENOMEM;return NULL;}return __real_strdup(s);}
