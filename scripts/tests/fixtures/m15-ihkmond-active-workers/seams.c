#define _GNU_SOURCE
#include <assert.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <ihk/ihk_host_user.h>
/* Synchronous local IHK/syslog seams only. All eventfd/epoll/IO/close are libc. */
_Static_assert(sizeof(struct ihk_device_get_kmsg_buf_desc)==16,"GET ABI");
_Static_assert(offsetof(struct ihk_device_get_kmsg_buf_desc,handle)==8,"GET field");
_Static_assert(sizeof(struct ihk_device_read_kmsg_buf_desc)==24,"READ ABI");
_Static_assert(offsetof(struct ihk_device_read_kmsg_buf_desc,buf)==16,"READ field");
_Static_assert(sizeof(struct ihk_os_ioctl_eventfd_desc)==8,"EVENT ABI");
_Static_assert(offsetof(struct ihk_os_ioctl_eventfd_desc,type)==4,"EVENT field");
extern int fixture_get(int,int,void **);
extern int fixture_read(int,void *,int,char *);
extern int fixture_release(int,void *);
extern int fixture_register(int,int,int);
extern void fixture_log_open(const char *,int,int);
extern void fixture_log_close(void);
extern void fixture_log_line(int,const char *,const char *);
int fixture_ioctl(int fd,unsigned long request,...){
 va_list args;va_start(args,request);void *argument=va_arg(args,void *);va_end(args);
 switch(request){
 case IHK_DEVICE_GET_KMSG_BUF:{struct ihk_device_get_kmsg_buf_desc *d=argument;assert(d);return fixture_get(fd,d->os_index,&d->handle);}
 case IHK_DEVICE_READ_KMSG_BUF:{const struct ihk_device_read_kmsg_buf_desc *d=argument;assert(d);return fixture_read(fd,d->handle,d->shift,d->buf);}
 case IHK_DEVICE_RELEASE_KMSG_BUF:return fixture_release(fd,argument);
 case IHK_OS_REGISTER_EVENT:{const struct ihk_os_ioctl_eventfd_desc *d=argument;assert(d);return fixture_register(fd,d->fd,d->type);}
 default:assert(!"unexpected local IHK ioctl");return -1;
 }
}
void fixture_openlog(const char *id,int option,int facility){fixture_log_open(id,option,facility);}
void fixture_closelog(void){fixture_log_close();}
void fixture_syslog(int priority,const char *format,...){
 va_list args;va_start(args,format);const char *text=va_arg(args,const char *);va_end(args);
 fixture_log_line(priority,format,text);
}
