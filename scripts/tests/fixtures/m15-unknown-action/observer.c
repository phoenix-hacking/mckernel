#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/eventfd.h>
#include <unistd.h>
extern int observed_main(int,char **);
static int source_fd=-1,opens,calls,closes,is_config;
int observation_open(const char *path,int flags,...){
 assert(opens==0&&!strcmp(path,is_config?"/dev/mcd0":"/dev/mcos0")&&flags==(is_config?O_RDWR:O_RDONLY));
 source_fd=eventfd(0,EFD_CLOEXEC);assert(source_fd>=0);++opens;return source_fd;
}
int observation_ioctl(int fd,unsigned long request,...){
 /* An unknown action has no payload contract. Never fetch a vararg. */
 (void)fd;(void)request;++calls;assert(!"unknown action unexpectedly dispatched ioctl");abort();
}
int observation_close(int fd){
 assert(fd==source_fd&&fd>=0&&opens==1&&calls==0&&closes==0);assert(close(fd)==0);++closes;
 errno=0;assert(fcntl(fd,F_GETFD)==-1&&errno==EBADF);errno=EDOM;return 0;
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
static void write_capture(const char *prefix,const char *suffix,const char *bytes,size_t size){char path[4096];assert(snprintf(path,sizeof(path),"%s%s",prefix,suffix)>0);FILE *out=fopen(path,"wb");assert(out);assert(fwrite(bytes,1,size,out)==size);assert(fclose(out)==0);}
int main(int argc,char **argv){
 assert(getuid()==1000&&geteuid()==1000&&argc==4);assert(!strcmp(argv[1],"ihkconfig")||!strcmp(argv[1],"ihkosctl"));is_config=!strcmp(argv[1],"ihkconfig");int expected=atoi(argv[2]);assert(expected==0||expected==1);
 struct fdset before=fdset();char name[32];strcpy(name,argv[1]);char zero[]="0",action[]="qurey";char *arguments[]={name,zero,action,NULL};
 struct capture out=capture_begin(1,stdout),err=capture_begin(2,stderr);int result=observed_main(3,arguments);char stdout_bytes[4096],stderr_bytes[4096];size_t out_size=capture_end(out,stdout_bytes,sizeof(stdout_bytes)),err_size=capture_end(err,stderr_bytes,sizeof(stderr_bytes));
 const char *diagnostics=is_config?"Unknown action : qurey\nUsage: ihkconfig (dev #) (action)\naction:\n    create\n    destroy\n    scratch\n    sbox\n    read\n    mmap\n    ioctl\n    clear_kmsg\n    clear_kmsg_write\n    reserve cpu|mem [resources]\n    release cpu|mem [resources]\n    query cpu|mem\n    get os_instances\n    get buildid\n":"Unknown action : qurey\nUsage: ihkosctl (dev #) (action)\naction:\n    load (kernel.img)\n    boot\n    shutdown\n    assign cpu|mem \n           cpu (cpu_list) \n           mem (size@NUMA) \n    release cpu|mem \n            cpu (cpu_list) \n            mem (size@NUMA) \n    set ikc_map (cpu_list:cpu+cpu_list:cpu+..) \n    get ikc_map\n    query [cpu|mem]\n    query_free_mem\n    kargs (kernel arg)\n    get status\n    kmsg\n    clear_kmsg\n    intr cpu irq_vector\n    ioctl (req) (arg)\n    dump [-d level] [file]\n";
 assert(result==expected&&opens==1&&calls==0&&closes==1&&out_size==0&&err_size==strlen(diagnostics)&&!memcmp(stderr_bytes,diagnostics,err_size));assert(!strcmp(name,argv[1])&&!strcmp(zero,"0")&&!strcmp(action,"qurey"));
 write_capture(argv[3],".main.stdout",stdout_bytes,out_size);write_capture(argv[3],".main.stderr",stderr_bytes,err_size);
 struct fdset after=fdset();assert(before.count==after.count&&!memcmp(before.values,after.values,before.count*sizeof(int)));
 printf("unknown-action mainFUNCTION tool=%s argv=0,qurey raw-main=%d opens=1 ioctl=0 closes=1 EBADF=1 stdout-bytes=%zu stderr-bytes=%zu exact-usage=1 inputs-unchanged=1 fd-restored=1 no-CRT-exit-claim=1\n",argv[1],result,out_size,err_size);return 0;
}
