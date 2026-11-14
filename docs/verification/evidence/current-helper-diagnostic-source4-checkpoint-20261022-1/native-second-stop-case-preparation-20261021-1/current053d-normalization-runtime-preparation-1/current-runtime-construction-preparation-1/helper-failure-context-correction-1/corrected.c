#define main collector_main_never_called
#define open fixture_open
#define fork fixture_fork
#include "/home/holden/mckernel-work/host-preparation/native-second-stop-case-preparation-20261021-1/current053d-normalization-runtime-preparation-1/current-runtime-construction-preparation-1/helper-failure-context-correction-1/native-second-stop-collector.helper-failure.c"
#undef main
#undef open
#undef fork
#include <sys/syscall.h>
#include <assert.h>
static pid_t children[4];static int child_count;
static const char *evidence_root;
int fixture_open(const char *path,int flags,...) {
 mode_t mode=0;if(flags&O_CREAT){va_list ap;va_start(ap,flags);mode=va_arg(ap,int);va_end(ap);}
 char mapped[4096];
 if(!strncmp(path,"/case/evidence/",15)){snprintf(mapped,sizeof mapped,"%s/%s",evidence_root,path+15);path=mapped;}
 else if(!strcmp(path,"/dev/kmsg")){snprintf(mapped,sizeof mapped,"%s/boot.kmsg",evidence_root);path=mapped;}
 return openat(AT_FDCWD,path,flags,mode);
}
pid_t fixture_fork(void){pid_t p=(pid_t)syscall(SYS_fork);if(p>0){assert(child_count<4);children[child_count++]=p;}return p;}
int main(int argc,char **argv){assert(argc==3);evidence_root=argv[1];assert(prctl(PR_SET_CHILD_SUBREAPER,1)==0);
 int safe=1;int failing=strcmp(argv[2],"success")!=0;int bounded=!strcmp(argv[2],"bounded");
 char *av[]={"sh","-c",bounded?"i=0; while [ $i -lt 1024 ]; do printf A; printf B >&2; i=$((i+1)); done; exit 7":(failing?"printf failure-out; printf failure-err >&2; exit 7":"printf success-out; exit 0"),NULL};
 int rc=helper("boot","/bin/sh",av,&safe);assert(rc==(failing?-1:0));assert(safe==1);
 if(!strcmp(argv[2],"two-failures")){char *later[]={"sh","-c","printf later-out; printf later-err >&2; exit 9",NULL};assert(helper("load-second","/bin/sh",later,&safe)==-1);}
 for(int i=0;i<child_count;i++){int status;errno=0;assert(waitpid(children[i],&status,WNOHANG)==-1&&errno==ECHILD);errno=0;assert(kill(-children[i],0)==-1&&errno==ESRCH);fprintf(stderr,"CONTROLLED_HELPER_JOIN pid=%ld direct_child_reaped=true group_absent=true\n",(long)children[i]);}
#ifdef CORRECTED
 assert((first_failed_helper_tag!=NULL)==failing);
 if(failing){assert(!strcmp(first_failed_helper_tag,"boot")&&first_failed_helper.status==(7<<8));assert(first_failed_helper.clean==1&&first_failed_helper.fault==0&&first_failed_helper.timeout==0);}
 assert(publish_helper_failure(STDOUT_FILENO)==0);
#endif
 return 0;}
