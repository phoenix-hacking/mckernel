#define _GNU_SOURCE
#include <assert.h>
#include <bfd.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pwd.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/eventfd.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>
#include <ihk/ihklib_private.h>
/* Genuine headers precede ALL explicitly typed local observation hooks. */
void *observation_malloc(size_t size);
void observation_free(void *pointer);
int observation_os_open(int index);
int observation_status(int index);
int observation_ioctl(int fd,unsigned long request,...);
int observation_close(int fd);
int observation_access(const char *path,int mode);
unsigned int observation_bfd_init(void);
bfd *observation_bfd_fopen(const char *path,const char *target,const char *mode,int fd);
bfd_boolean observation_bfd_close(bfd *file);
typedef int (*Dump)(int,char *,int,int);
int observation_run(Dump dump);
