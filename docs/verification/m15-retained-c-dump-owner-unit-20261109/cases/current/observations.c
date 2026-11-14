#include "observations.h"
static void *owners[2];
static int scenario,attempts,allocations,live,frees,free_calls,free_entry[2];
static int fd,opens,closes,statuses,commands,conts,inits,parents,bfd_opens;
static char filename[32],original[32],events[64];static size_t event_count;
static void event(char value){assert(event_count+1<sizeof(events));events[event_count++]=value;events[event_count]=0;}
static int expected_live(void){return scenario;}
void *observation_malloc(size_t size){
 assert(attempts<2&&size==(attempts==0?sizeof(dump_mem_chunks_t):0x100000UL));event('A');int position=attempts++;
 if((scenario==0&&position==0)||(scenario==1&&position==1)){errno=ENOMEM;return NULL;}
 void *pointer=malloc(size);assert(pointer);owners[position]=pointer;++allocations;++live;return pointer;
}
void observation_free(void *pointer){
 assert(closes==1&&conts==1&&free_calls<2);int position=free_calls==0?1:0;assert(pointer==owners[position]);free_entry[free_calls++]=errno;
 if(pointer){owners[position]=NULL;--live;++frees;event('F');}else event('n');
 free(pointer);errno=EDOM;
}
int observation_os_open(int index){assert(index==17&&opens==0&&live==0);fd=eventfd(0,EFD_CLOEXEC);assert(fd>=0);++opens;event('O');return fd;}
int observation_status(int index){assert(index==17&&opens==1&&statuses==0);++statuses;event('S');return IHK_STATUS_RUNNING;}
int observation_ioctl(int descriptor,unsigned long request,...){
 assert(descriptor==fd&&fd>=0&&request==IHK_OS_DUMP&&fcntl(fd,F_GETFD)>=0);
 va_list ap;va_start(ap,request);dumpargs_t *args=va_arg(ap,dumpargs_t *);va_end(ap);assert(args);
 /* Read ONLY fields already initialized by this exact production command.
  * In particular C spare/start and CONT buf/size are never read. */
 const int ordinary[]={DUMP_SET_LEVEL,DUMP_NMI,DUMP_QUERY_NUM_MEM_AREAS,DUMP_QUERY_MEM_AREAS,DUMP_NMI_CONT};
 assert(commands>=0&&commands<(scenario==0?4:5));int expected=scenario==0&&commands==3?DUMP_NMI_CONT:ordinary[commands];assert(args->cmd==expected);
 if(commands<2)assert(args->level==24);
 if(args->cmd==DUMP_SET_LEVEL)event('L');
 else if(args->cmd==DUMP_NMI)event('N');
 else if(args->cmd==DUMP_QUERY_NUM_MEM_AREAS){assert(args->size==0);args->size=(long)sizeof(dump_mem_chunks_t);event('Q');}
 else if(args->cmd==DUMP_QUERY_MEM_AREAS){
  assert(live==1&&owners[0]&&args->buf==owners[0]&&args->size==(long)sizeof(dump_mem_chunks_t));
  for(size_t i=0;i<sizeof(dump_mem_chunks_t);i++)assert(((unsigned char *)args->buf)[i]==0);
  dump_mem_chunks_t *chunks=args->buf;chunks->nr_chunks=0;chunks->kernel_base=0;chunks->phys_start=0;event('M');
 }else{assert(args->cmd==DUMP_NMI_CONT&&conts==0&&live==expected_live());++conts;event('T');errno=EINTR;}
 ++commands;return 0;
}
int observation_close(int descriptor){
 assert(descriptor==fd&&descriptor>=0&&closes==0&&conts==1&&live==expected_live()&&free_calls==0);assert(close(descriptor)==0);errno=0;assert(fcntl(descriptor,F_GETFD)==-1&&errno==EBADF);fd=-1;++closes;event('C');errno=ERANGE;return 0;
}
unsigned int observation_bfd_init(void){assert(scenario==2&&commands==4&&live==2&&inits==0);++inits;event('B');return 0;}
int observation_access(const char *path,int mode){assert(scenario==2&&mode==W_OK&&inits==1&&live==2&&parents==0&&!strcmp(path,"/")&&filename[0]==0);++parents;event('P');return 0;}
bfd *observation_bfd_fopen(const char *path,const char *target,const char *mode,int descriptor){assert(scenario==2&&inits==1&&commands==4&&live==2&&bfd_opens==0&&target==NULL&&!strcmp(mode,"w")&&descriptor==-1&&path==filename&&!memcmp(filename,original,sizeof(filename)));++bfd_opens;event('X');errno=EDOM;return NULL;}
bfd_boolean observation_bfd_close(bfd *file){(void)file;abort();}
int observation_run(Dump dump){
 assert(getuid()==1000&&geteuid()==1000);
 const char *orders[]={"OSLNQATCnn","OSLNQAMATCnF","OSLNQAMABPXTCFF"};
 for(int number=0;number<3;number++){
  assert(live==0);scenario=number;attempts=allocations=frees=free_calls=opens=closes=statuses=commands=conts=inits=parents=bfd_opens=0;fd=-1;event_count=0;events[0]=0;memset(owners,0,sizeof(owners));memset(free_entry,0,sizeof(free_entry));memset(filename,0,sizeof(filename));strcpy(filename,"/dumpfile");memcpy(original,filename,sizeof(original));
  errno=19;int result=dump(17,filename,24,0);int observed_errno=errno;
  assert(result==(number==2?-EINVAL:-ENOMEM)&&attempts==(number==0?1:2)&&allocations==number&&frees==number&&live==0&&owners[0]==NULL&&owners[1]==NULL);
  assert(opens==1&&statuses==1&&closes==1&&conts==1&&fd==-1&&commands==(number==0?4:5)&&free_calls==2&&free_entry[0]==ERANGE&&free_entry[1]==EDOM&&observed_errno==ERANGE);
  assert(inits==(number==2)&&parents==(number==2)&&bfd_opens==(number==2)&&!memcmp(filename,original,sizeof(filename))&&!strcmp(events,orders[number]));
  printf("CASE C-scoped owners=%d result=%d owned-frees=%d survivor=0 free-calls=2 close-once=1 EBADF=1 CONT=1 group-entry-errno=%d restored=%d order=%s\n",number,result,frees,free_entry[0],observed_errno,events);
 }
 puts("retained-C-dump-owner cases=3 zero-partial-both buffers genuine-libc once-cleanup after-last-borrow no-real-device-or-BFD-object");return 0;
}

int ihk_os_makedumpfile(int index,char *path,int level,int interactive);
int main(void){return observation_run(ihk_os_makedumpfile);}
