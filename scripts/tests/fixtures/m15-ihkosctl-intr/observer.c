#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <ihk/ihk_host_user.h>
_Static_assert(IHK_OS_DEBUG_START==0x122a00,"selected interrupt request");
extern int observed_main(int,char **);
static int source_fd=-1,opens,calls,closes,failure,expected_scalar;
int observation_open(const char *path,int flags,...){
 assert(!strcmp(path,"/dev/mcos0")&&flags==O_RDONLY&&opens==0);
 source_fd=memfd_create("intr-cli-local",MFD_CLOEXEC);assert(source_fd>=0);++opens;return source_fd;
}
int observation_ioctl(int fd,unsigned long request,...){
 assert(fd==source_fd&&opens==1&&calls==0&&closes==0);assert(fcntl(fd,F_GETFD)>=0);
 /* This request's payload is promoted int in BOTH actual CLI sources. */
 switch(request){
 case IHK_OS_DEBUG_START:{va_list args;va_start(args,request);int value=va_arg(args,int);va_end(args);assert(value==expected_scalar);break;}
 default:assert(!"unexpected intr ioctl request");abort();
 }
 ++calls;if(failure){errno=EIO;return -1;}return 0;
}
int observation_close(int fd){
 assert(fd==source_fd&&opens==1&&calls==1&&closes==0);assert(close(fd)==0);++closes;
 errno=0;assert(fcntl(fd,F_GETFD)==-1&&errno==EBADF);
 errno=EDOM; /* Main must return its captured result after the genuine close. */
 return 0;
}
struct fdset{int values[64];size_t count;};
static int compare(const void *a,const void *b){int x=*(const int*)a,y=*(const int*)b;return (x>y)-(x<y);}
static struct fdset fdset(void){
 struct fdset result={0};DIR *directory=opendir("/proc/self/fd");assert(directory);int scanner=dirfd(directory);struct dirent *entry;
 while((entry=readdir(directory))){char *end;long value=strtol(entry->d_name,&end,10);if(!*entry->d_name||*end||value==scanner)continue;assert(result.count<64);result.values[result.count++]=(int)value;}
 assert(closedir(directory)==0);qsort(result.values,result.count,sizeof(int),compare);return result;
}
struct capture{int target,read_fd,saved;FILE *stream;};
static struct capture capture_begin(int target,FILE *stream){
 assert(fflush(stream)==0);int pipes[2];assert(pipe2(pipes,O_CLOEXEC)==0);int saved=dup(target);assert(saved>=0);assert(dup2(pipes[1],target)==target);assert(close(pipes[1])==0);return (struct capture){target,pipes[0],saved,stream};
}
static size_t capture_end(struct capture value,char *output,size_t capacity){
 assert(fflush(value.stream)==0);assert(dup2(value.saved,value.target)==value.target);assert(close(value.saved)==0);size_t size=0;
 for(;;){assert(size<capacity);ssize_t count=read(value.read_fd,output+size,capacity-size);if(count<0&&errno==EINTR)continue;assert(count>=0);if(!count)break;size+=(size_t)count;}
 assert(close(value.read_fd)==0);return size;
}
static void check(int baseline,int shape,int fail){
 struct fdset before=fdset();source_fd=-1;opens=calls=closes=0;failure=fail;expected_scalar=(int[]){0xf1,0xf2,0x2f3}[shape];
 char *argv0[]={"ihkosctl","0","intr",NULL};char *argv1[]={"ihkosctl","0","intr","242",NULL};char *argv2[]={"ihkosctl","0","intr","2","243",NULL};char **arguments=(char **[]){argv0,argv1,argv2}[shape];
 struct capture out=capture_begin(1,stdout),err=capture_begin(2,stderr);
 int result=observed_main(shape+3,arguments);
 char stdout_bytes[128],stderr_bytes[128];size_t out_size=capture_end(out,stdout_bytes,sizeof(stdout_bytes)),err_size=capture_end(err,stderr_bytes,sizeof(stderr_bytes));
 assert(opens==1&&calls==1&&closes==1&&out_size==0);assert(result==(fail&&!baseline?-1:0));
 const char *expected=fail?"error: sending IRQ\n":"";assert(err_size==strlen(expected)&&!memcmp(stderr_bytes,expected,err_size));
 struct fdset after=fdset();assert(before.count==after.count&&!memcmp(before.values,after.values,before.count*sizeof(int)));
 printf("CASE shape=%d scalar=0x%x request=0x122a00 ioctl=%d raw-main=%d opens=1 calls=1 closes=1 EBADF=1 stderr-bytes=%zu fd-restored=1\n",shape,expected_scalar,fail?-1:0,result,err_size);
}
int main(int argc,char **argv){
 assert(getuid()==1000&&geteuid()==1000&&argc==2);int baseline=atoi(argv[1]);assert(baseline==0||baseline==1);
 for(int shape=0;shape<3;shape++)for(int fail=0;fail<2;fail++)check(baseline,shape,fail);
 printf("intr-cli whole-main-function cases=6 baseline=%d false-successes=%d genuine-memfd-close=6 no-CRT-exit-claim=1\n",baseline,baseline?3:0);return 0;
}
