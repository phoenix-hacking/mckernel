#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <sys/stat.h>
#include <ihk/ihk_host_user.h>
/* Existing selected_target_stat_dirent_ABI.c public-stat oracle, retained in
 * this required C seam compile. Monitor storage is unread opaque256/align8. */
_Static_assert(sizeof(struct stat)==144 && _Alignof(struct stat)==8,"selected HOST stat144/8");
_Static_assert(__builtin_types_compatible_p(__typeof__(&stat),int(*)(const char*,struct stat*)),"selected public stat prototype");
_Static_assert(sizeof(struct stat)<=256 && _Alignof(struct stat)<=8,"fits actual opaque monitor storage");
#ifndef ACTIVE_MONITOR_STAT_PATH
#error "Explicit owned regular-file stat mapping is required"
#endif
extern void monitor_stat_observed(int,int);
extern int monitor_detect(int,unsigned long);
int fixture_stat(const char *path,void *output){
 assert(path && !strcmp(path,"/dev/mcos0"));assert(output && (uintptr_t)output%8==0);
 /* No syscall is issued on path. Genuine stat owns every output byte/result. */
 int result=stat(ACTIVE_MONITOR_STAT_PATH,(struct stat *)output);int saved_errno=errno;
 monitor_stat_observed(result,saved_errno);errno=saved_errno;return result;
}
int fixture_ioctl(int fd,unsigned long request,...){
 /* Dispatch BEFORE vararg access: DETECT's third argument is scalar c_ulong. */
 switch(request){
 case IHK_DEVICE_DETECT_HUNGUP:{va_list args;va_start(args,request);unsigned long device=va_arg(args,unsigned long);va_end(args);return monitor_detect(fd,device);}
 default:assert(!"unexpected monitor IHK ioctl");return -1;
 }
}
void fixture_openlog(const char *id,int option,int facility){(void)id;(void)option;(void)facility;assert(!"monitor must not open kmsg syslog");}
void fixture_closelog(void){assert(!"monitor must not close kmsg syslog");}
void fixture_syslog(int priority,const char *format,...){(void)priority;(void)format;assert(!"monitor must not call kmsg syslog");}
