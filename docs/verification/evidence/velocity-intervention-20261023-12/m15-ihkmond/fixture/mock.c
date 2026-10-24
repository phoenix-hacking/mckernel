/* TEST ONLY: synthetic udev/epoll/eventfd/kernel endpoints, real Rust threads.
 * Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <pthread.h>
#include <sys/epoll.h>
#include <sys/signalfd.h>
#include <sys/stat.h>
#include <dirent.h>
#include <time.h>
#include <signal.h>
#include <libudev.h>
#include <ihk/ihklib.h>
_Static_assert(sizeof(struct epoll_event)==12,"epoll ABI");
_Static_assert(sizeof(sigset_t)==128,"sigset ABI");
_Static_assert(sizeof(struct stat)<=256&&_Alignof(struct stat)<=8,"stat opaque ABI");
_Static_assert(sizeof(struct ihk_device_get_kmsg_buf_desc)==16,"get descriptor ABI");
_Static_assert(sizeof(struct ihk_device_read_kmsg_buf_desc)==24,"read descriptor ABI");
enum{EVENT=1,EP,KMSG,STATUS,SIGNAL,UDEVFD,DEV,KLOG};
struct entry{int kind,open,nwatch,watch[8];uint64_t counter;};
static struct entry fds[4096];static int nextfd=1000,udevfd=-1,signal_fd=-1;
static int phase,cycle,kstage,reads,detects,lease_gets,releases,attempts,leases,ctxrefs,monrefs,devrefs,duplicates;
static int pending,syscount;static size_t sysbytes;
static pthread_mutex_t state=PTHREAD_MUTEX_INITIALIZER,logging=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed=PTHREAD_COND_INITIALIZER;
static const char *mode(void){const char *p=getenv("IHKMOND_SCENARIO");return p?p:"lifecycle";}
static int ismode(const char *s){return !strcmp(mode(),s);}
static int setting(const char *key,int def){const char *p=getenv(key);return p?atoi(p):def;}
static void emit(const char *fmt,...){pthread_mutex_lock(&logging);const char *p=getenv("IHKMOND_TRACE");FILE *o=p?fopen(p,"a"):NULL;if(!o)abort();va_list a;va_start(a,fmt);vfprintf(o,fmt,a);va_end(a);fputc('\n',o);fclose(o);pthread_mutex_unlock(&logging);}
static void message(const char *kind,const char *bytes,size_t n){pthread_mutex_lock(&logging);FILE *o=fopen(getenv("IHKMOND_TRACE"),"a");if(!o)abort();fprintf(o,"%s bytes=%zu hex=",kind,n);for(size_t i=0;i<n&&i<512;i++)fprintf(o,"%02x",(unsigned char)bytes[i]);fputc('\n',o);fclose(o);pthread_mutex_unlock(&logging);}
void fixture_printk(const char *fmt,...){char b[3840];va_list a;va_start(a,fmt);vsnprintf(b,sizeof(b),fmt,a);va_end(a);message("kprint",b,strlen(b));}
static int alloc_locked(int kind){int fd=nextfd++;if(fd>=4096)abort();fds[fd].kind=kind;fds[fd].open=1;emit("alloc fd=%d kind=%d",fd,kind);return fd;}
static int fake(int fd){return fd>=1000&&fd<4096;}
static void close_locked(int fd){if(!fds[fd].open){duplicates++;emit("duplicate-close fd=%d",fd);}else{fds[fd].open=0;emit("close fd=%d kind=%d",fd,fds[fd].kind);}pthread_cond_broadcast(&changed);}
int __real_close(int);ssize_t __real_read(int,void *,size_t);ssize_t __real_write(int,const void *,size_t);int __real_open(const char *,int,...);int __real_stat(const char *,struct stat *);
int __wrap_close(int fd){if(!fake(fd))return __real_close(fd);pthread_mutex_lock(&state);close_locked(fd);pthread_mutex_unlock(&state);return 0;}
uid_t __wrap_geteuid(void){return 0;}
int __wrap_open(const char *path,int flags,...){if(!strcmp(path,"/dev/kmsg")){pthread_mutex_lock(&state);int fd=alloc_locked(KLOG);pthread_mutex_unlock(&state);return fd;}mode_t m=0;if(flags&O_CREAT){va_list a;va_start(a,flags);m=va_arg(a,int);va_end(a);}return __real_open(path,flags,m);}
int __wrap_stat(const char *path,struct stat *out){if(!strncmp(path,"/dev/mcos",9)){memset(out,0,sizeof(*out));emit("stat %s",path);return 0;}return __real_stat(path,out);}
ssize_t __wrap_write(int fd,const void *buf,size_t n){if(!fake(fd))return __real_write(fd,buf,n);pthread_mutex_lock(&state);int kind=fds[fd].kind;if(kind==KLOG){pthread_mutex_unlock(&state);size_t size=n;if(size&&((const char*)buf)[size-1]==0)size--;message("kprint",buf,size);return n;}if(kind==EVENT&&n==8){fds[fd].counter+=*(const uint64_t*)buf;emit("notify fd=%d",fd);pthread_cond_broadcast(&changed);pthread_mutex_unlock(&state);return 8;}pthread_mutex_unlock(&state);errno=EINVAL;return -1;}
ssize_t __wrap_read(int fd,void *buf,size_t n){if(!fake(fd))return __real_read(fd,buf,n);pthread_mutex_lock(&state);int kind=fds[fd].kind;if(kind==SIGNAL&&n>=128){memset(buf,0,128);*(uint32_t*)buf=SIGTERM;emit("stop-signal");pthread_mutex_unlock(&state);return 128;}if(n>=8&&(kind==EVENT||kind==KMSG||kind==STATUS)){*(uint64_t*)buf=fds[fd].counter;fds[fd].counter=0;emit("reap fd=%d",fd);pthread_cond_broadcast(&changed);pthread_mutex_unlock(&state);return 8;}pthread_mutex_unlock(&state);errno=EINVAL;return -1;}
int __wrap_daemon(int nochdir,int noclose){emit("daemon %d %d",nochdir,noclose);if(ismode("daemon-fail")){errno=EPERM;return -1;}return 0;}
int __wrap_eventfd(unsigned int value,int flags){pthread_mutex_lock(&state);int fd=alloc_locked(EVENT);fds[fd].counter=value;pthread_mutex_unlock(&state);return fd;}
int __wrap_signalfd(int old,const sigset_t *mask,int flags){(void)old;(void)mask;(void)flags;pthread_mutex_lock(&state);signal_fd=alloc_locked(SIGNAL);pthread_mutex_unlock(&state);return signal_fd;}
int __wrap_epoll_create(int size){(void)size;pthread_mutex_lock(&state);int fd=alloc_locked(EP);pthread_mutex_unlock(&state);return fd;}
int __wrap_epoll_ctl(int ep,int op,int fd,struct epoll_event *event){(void)event;pthread_mutex_lock(&state);if(op==EPOLL_CTL_ADD){if(ismode("ctl-status-fail")&&fds[fd].kind==STATUS){pthread_mutex_unlock(&state);errno=EIO;return -1;}if(fds[ep].nwatch>=8)abort();fds[ep].watch[fds[ep].nwatch++]=fd;}else{for(int i=0;i<fds[ep].nwatch;i++)if(fds[ep].watch[i]==fd){memmove(&fds[ep].watch[i],&fds[ep].watch[i+1],(fds[ep].nwatch-i-1)*sizeof(int));fds[ep].nwatch--;break;}}emit("epoll_ctl ep=%d op=%d fd=%d",ep,op,fd);pthread_cond_broadcast(&changed);pthread_mutex_unlock(&state);return 0;}
static int findkind(int ep,int kind){for(int i=0;i<fds[ep].nwatch;i++){int fd=fds[ep].watch[i];if(fds[fd].kind==kind)return fd;}return -1;}
static int result_event(struct epoll_event *event,int fd){memset(event,0,sizeof(*event));event->events=EPOLLIN;event->data.fd=fd;pthread_mutex_unlock(&state);return 1;}
static void delay(void){struct timespec ts;clock_gettime(CLOCK_REALTIME,&ts);ts.tv_nsec+=10000000;if(ts.tv_nsec>=1000000000){ts.tv_nsec-=1000000000;ts.tv_sec++;}pthread_cond_timedwait(&changed,&state,&ts);}
int __wrap_epoll_wait(int ep,struct epoll_event *events,int max,int timeout){(void)max;pthread_mutex_lock(&state);for(;;){
 int main=findkind(ep,UDEVFD)>=0,kmsg=findkind(ep,KMSG),status=findkind(ep,STATUS);
 if(main&&ismode("main-epoll-fail")){pthread_mutex_unlock(&state);errno=EIO;return -1;}
 for(int i=0;i<fds[ep].nwatch;i++){int fd=fds[ep].watch[i];if(fds[fd].kind==EVENT&&fds[fd].counter)return result_event(events,fd);}
 if(main){
  if(ismode("frontend")||ismode("help")){if(phase==0){pending=1;phase++;}else if(phase==1){pending=2;phase++;}else{pending=3;}return result_event(events,udevfd);}
  if(phase==0){pending=1;phase=1;return result_event(events,udevfd);}
  int want_k=setting("IHKMOND_EXPECT_KMSG",1),want_m=setting("IHKMOND_EXPECT_MON",1);
  if(phase==1&&(!want_k||kstage>=2)&&(!want_m||detects>=cycle+1)){
   if(ismode("stop-active")){phase=3;return result_event(events,signal_fd);}pending=2;phase=2;return result_event(events,udevfd);
  }
  int endpoints=0;for(int fd=1000;fd<nextfd;fd++)if(fds[fd].open&&(fds[fd].kind==KMSG||fds[fd].kind==STATUS))endpoints++;
  if(phase==2&&leases==0&&endpoints==0){if(ismode("repeat")&&cycle==0){cycle++;phase=0;continue;}phase=3;return result_event(events,signal_fd);}
 }else if(kmsg>=0&&status>=0){if(kstage==0){kstage=1;fds[kmsg].counter=1;pthread_cond_broadcast(&changed);return result_event(events,kmsg);}if(kstage==1){kstage=2;fds[status].counter=1;pthread_cond_broadcast(&changed);return result_event(events,status);}}
 else if(timeout>=0){delay();pthread_mutex_unlock(&state);return 0;}
 delay();
 }}
int ihklib_device_open(int index){pthread_mutex_lock(&state);int fd=alloc_locked(DEV);pthread_mutex_unlock(&state);emit("ihklib_device_open index=%d",index);return fd;}
int ihk_os_get_eventfd(int index,int type){emit("ihk_os_get_eventfd index=%d type=%d",index,type);if((ismode("kmsg-eventfd-fail")&&type==101)||(ismode("status-eventfd-fail")&&type==2)){errno=EIO;return -5;}pthread_mutex_lock(&state);int fd=alloc_locked(type==101?KMSG:STATUS);pthread_mutex_unlock(&state);return fd;}
int __wrap_ioctl(int fd,unsigned long req,...){va_list ap;va_start(ap,req);pthread_mutex_lock(&state);int ret=0;emit("ioctl fd=%d req=%lx",fd,req);
 if(req==IHK_DEVICE_DETECT_HUNGUP){(void)va_arg(ap,unsigned long);detects++;}
 else if(req==IHK_DEVICE_GET_KMSG_BUF){struct ihk_device_get_kmsg_buf_desc *d=va_arg(ap,void*);if(ismode("get-handle-fail")){ret=-5;}else{d->handle=(void*)(uintptr_t)(0x123400+lease_gets);lease_gets++;leases++;reads=0;kstage=0;}}
 else if(req==IHK_DEVICE_RELEASE_KMSG_BUF){(void)va_arg(ap,void*);attempts++;if(ismode("release-fail"))ret=-5;else{leases--;releases++;}}
 else if(req==IHK_DEVICE_READ_KMSG_BUF){struct ihk_device_read_kmsg_buf_desc *d=va_arg(ap,void*);if(ismode("read-fail")){ret=-5;}else{if(ismode("oversize")){size_t n=reads==0?(1U<<20)+17:0;memset(d->buf,'a',n);if(n)d->buf[n-1]='\n';ret=n;reads++;}else{const char *p=reads==0?"alpha\n\nbeta\n":reads==1?"panic\n":"tail\n";size_t n=strlen(p);memcpy(d->buf,p,n);ret=n;reads++;}}}
 va_end(ap);pthread_cond_broadcast(&changed);pthread_mutex_unlock(&state);if(ret<0)errno=EIO;return ret;
}
struct udev *udev_new(void){emit("udev_new");if(ismode("udev-new-fail"))return NULL;pthread_mutex_lock(&state);ctxrefs++;pthread_mutex_unlock(&state);return (void*)1;}
struct udev *udev_unref(struct udev *p){if(p){pthread_mutex_lock(&state);ctxrefs--;pthread_mutex_unlock(&state);}emit("udev_unref");return NULL;}
struct udev_monitor *udev_monitor_new_from_netlink(struct udev *p,const char *name){(void)p;emit("udev_monitor_new %s",name);if(ismode("monitor-new-fail"))return NULL;pthread_mutex_lock(&state);monrefs++;udevfd=alloc_locked(UDEVFD);pthread_mutex_unlock(&state);return (void*)2;}
int udev_monitor_filter_add_match_subsystem_devtype(struct udev_monitor *p,const char *sub,const char *dev){(void)p;(void)dev;emit("udev_filter %s",sub);return ismode("filter-fail")?-5:0;}
int udev_monitor_enable_receiving(struct udev_monitor *p){(void)p;return ismode("enable-fail")?-5:0;}
int udev_monitor_get_fd(struct udev_monitor *p){(void)p;return udevfd;}
struct udev_monitor *udev_monitor_unref(struct udev_monitor *p){if(p){pthread_mutex_lock(&state);monrefs--;close_locked(udevfd);pthread_mutex_unlock(&state);}emit("udev_monitor_unref");return NULL;}
struct fake_device{char action[16];char node[64];};
struct udev_device *udev_monitor_receive_device(struct udev_monitor *p){(void)p;pthread_mutex_lock(&state);int action=pending;if(action==3){pthread_mutex_unlock(&state);return NULL;}struct fake_device *d=calloc(1,sizeof(*d));strcpy(d->action,action==1?"add":"remove");strcpy(d->node,"/dev/mcos0");devrefs++;emit("udev_device action=%s",d->action);pthread_mutex_unlock(&state);return (void*)d;}
const char *udev_device_get_devnode(struct udev_device *p){return ((struct fake_device*)p)->node;}
const char *udev_device_get_action(struct udev_device *p){return ((struct fake_device*)p)->action;}
struct udev_device *udev_device_unref(struct udev_device *p){if(p){pthread_mutex_lock(&state);devrefs--;pthread_mutex_unlock(&state);free(p);}emit("udev_device_unref");return NULL;}
void openlog(const char *id,int options,int facility){emit("openlog id=%s options=%d facility=%d",id,options,facility);}
void closelog(void){emit("closelog");}
void syslog(int priority,const char *format,...){(void)format;va_list ap;va_start(ap,format);const char *line=va_arg(ap,const char*);size_t n=strlen(line);pthread_mutex_lock(&state);syscount++;sysbytes+=n;pthread_mutex_unlock(&state);message("syslog",line,n);emit("priority=%d",priority);va_end(ap);}
static void summary(void){int count=0;DIR *tasks=opendir("/proc/self/task");if(tasks){struct dirent *e;while((e=readdir(tasks)))if(e->d_name[0]!='.')count++;closedir(tasks);}pthread_mutex_lock(&state);int open=0;for(int i=1000;i<nextfd;i++)open+=fds[i].open;FILE *o=fopen(getenv("IHKMOND_SUMMARY"),"w");if(!o)abort();fprintf(o,"{\"open_fds\":%d,\"duplicate_close\":%d,\"leases\":%d,\"udev_ctx\":%d,\"udev_mon\":%d,\"udev_devices\":%d,\"syslog_messages\":%d,\"syslog_bytes\":%zu,\"detect\":%d,\"get\":%d,\"read_last_session\":%d,\"released\":%d,\"release_attempts\":%d,\"threads\":%d}\n",open,duplicates,leases,ctxrefs,monrefs,devrefs,syscount,sysbytes,detects,lease_gets,reads,releases,attempts,count);fclose(o);pthread_mutex_unlock(&state);}
__attribute__((constructor))static void init(void){atexit(summary);}
