#define main collector_main_never_called
#define open fixture_open
#define fork fixture_fork
#include "/home/holden/mckernel-work/host-preparation/M07-current-profile-next-observation-preparation-20261021-1/boot-collector-profile-correction-1/bounded-compile-correction-1/collector-helper-failure-context.c"
#undef main
#undef open
#undef fork
#include <sys/syscall.h>
#include <assert.h>
static pid_t controlled_child;
static const char *evidence_root;
int fixture_open(const char *path,int flags,...) {
 mode_t mode=0;if(flags&O_CREAT){va_list ap;va_start(ap,flags);mode=va_arg(ap,int);va_end(ap);}
 char mapped[4096];if(!strncmp(path,"/case/evidence/",15)){snprintf(mapped,sizeof mapped,"%s/%s",evidence_root,path+15);path=mapped;}
 return openat(AT_FDCWD,path,flags,mode);
}
pid_t fixture_fork(void){pid_t p=(pid_t)syscall(SYS_fork);if(p>0)controlled_child=p;return p;}
int main(int argc,char **argv){assert(argc==3);evidence_root=argv[1];assert(prctl(PR_SET_CHILD_SUBREAPER,1)==0);
 int safe=1;int failing=!strcmp(argv[2],"failure");
 char *av[]={"sh","-c",failing?"printf failure-out; printf failure-err >&2; exit 7":"printf success-out; exit 0",NULL};
 int rc=helper("boot","/bin/sh",av,&safe);assert(rc==(failing?-1:0));assert(safe==1);assert(controlled_child>0);
 int status;errno=0;assert(waitpid(controlled_child,&status,WNOHANG)==-1&&errno==ECHILD);errno=0;assert(kill(-controlled_child,0)==-1&&errno==ESRCH);
#ifdef CORRECTED
 assert((first_failed_helper_tag!=NULL)==failing);
 if(failing){assert(first_failed_helper.status==(7<<8));assert(first_failed_helper.clean==1&&first_failed_helper.fault==0&&first_failed_helper.timeout==0);}
 assert(publish_helper_failure(STDOUT_FILENO)==0);
#endif
 fprintf(stderr,"CONTROLLED_HELPER_JOIN pid=%ld direct_child_reaped=true group_absent=true safe=%d rc=%d\n",(long)controlled_child,safe,rc);
 return 0;}
