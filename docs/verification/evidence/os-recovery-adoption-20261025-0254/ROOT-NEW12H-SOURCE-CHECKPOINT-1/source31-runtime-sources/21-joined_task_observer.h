/* TEST FIXTURE ONLY. Functional McKernel OS/apps and Rust/assembly migration only;
 * no security testing. Real pthread targets/results are preserved. Only the
 * terminal observer waits; its unchanged external Owner.run deadline is8s.
 */
#include <sys/syscall.h>
#include <sched.h>
#define JOINED_TASK_LIMIT 64
struct joined_task {
 pthread_t handle; int handle_valid,started,created,create_result,joined,join_result,absent;
 pid_t tid; unsigned long long birth; char initial_stat[4096];
 void *(*function)(void *); void *argument;
};
static struct joined_task joined_tasks[JOINED_TASK_LIMIT];
static size_t joined_task_count;
static int joined_tracking_invalid;
static pthread_mutex_t joined_task_lock=PTHREAD_MUTEX_INITIALIZER;
int __real_pthread_create(pthread_t *,const pthread_attr_t *,void *(*)(void *),void *);
int __real_pthread_join(pthread_t,void **);
static FILE *joined_audit(void){
 const char *path=getenv("IHKMOND_JOIN_AUDIT");if(!path||!*path)abort();
 FILE *file=fopen(path,"a");if(!file)abort();return file;
}
static void joined_audit_close(FILE *file){int error=ferror(file);if(fclose(file)||error)abort();}
static void joined_quote(FILE *file,const char *text){
 fputc('"',file);for(const unsigned char *p=(const unsigned char*)text;*p;p++){
  if(*p=='"'||*p=='\\')fputc('\\',file);
  if(*p<32)fprintf(file,"\\u%04x",*p);else fputc(*p,file);
 }fputc('"',file);
}
/* 1=complete stat with exact numeric PID/birth,0=typed ENOENT,-1=other failure. */
static int joined_stat(pid_t tid,char raw[4096],unsigned long long *birth){
 char path[80];snprintf(path,sizeof(path),"/proc/self/task/%d/stat",tid);
 FILE *file=fopen(path,"r");if(!file)return errno==ENOENT?0:-1;
 if(!fgets(raw,4096,file)){fclose(file);return -1;}int complete=strchr(raw,'\n')!=NULL;
 if(fclose(file)||!complete)return -1;raw[strcspn(raw,"\n")]=0;
 char *end;errno=0;long pid=strtol(raw,&end,10);if(errno||pid!=tid||strncmp(end," (",2))return -1;
 char *right=strrchr(raw,')');if(!right||right[1]!=' ')return -1;
 char fields[4096];strcpy(fields,right+2);char *save=NULL,*token=strtok_r(fields," ",&save);
 if(!token||strlen(token)!=1||!strchr("RSDZTtXxKWPI",token[0]))return -1;
 for(int field=4;field<=22;field++){token=strtok_r(NULL," ",&save);if(!token)return -1;}
 if(*token<'0'||*token>'9')return -1;
 errno=0;*birth=strtoull(token,&end,10);return errno||*end||!*birth?-1:1;
}
static void joined_event(const char *event,size_t slot,int result){
 FILE *file=joined_audit();struct joined_task *task=&joined_tasks[slot];
 fprintf(file,"{\"event\":\"%s\",\"slot\":%zu,\"tid\":%d,\"birth\":%llu,\"result\":%d,\"initial_raw_stat\":",event,slot,task->tid,task->birth,result);
 joined_quote(file,task->initial_stat);fputs("}\n",file);joined_audit_close(file);
}
static void *joined_start(void *argument){
 struct joined_task *task=argument;pthread_mutex_lock(&joined_task_lock);
 task->tid=(pid_t)syscall(SYS_gettid);
 int result=joined_stat(task->tid,task->initial_stat,&task->birth);
 if(result!=1)joined_tracking_invalid=1;
 for(size_t i=0;i<joined_task_count;i++)if(&joined_tasks[i]!=task&&joined_tasks[i].started&&joined_tasks[i].tid==task->tid)joined_tracking_invalid=1;
 task->started=1;joined_event("thread_start",(size_t)(task-joined_tasks),result);
 pthread_mutex_unlock(&joined_task_lock);
 return task->function(task->argument);
}
int __wrap_pthread_create(pthread_t *handle,const pthread_attr_t *attributes,void *(*function)(void *),void *argument){
 pthread_mutex_lock(&joined_task_lock);
 if(joined_task_count==JOINED_TASK_LIMIT){
  joined_tracking_invalid=1;pthread_mutex_unlock(&joined_task_lock);
  return __real_pthread_create(handle,attributes,function,argument);
 }
 size_t slot=joined_task_count++;struct joined_task *task=&joined_tasks[slot];task->function=function;task->argument=argument;
 pthread_mutex_unlock(&joined_task_lock);
 int result=__real_pthread_create(handle,attributes,joined_start,task);
 pthread_mutex_lock(&joined_task_lock);task->create_result=result;task->created=result==0;
 if(!result){task->handle=*handle;task->handle_valid=1;}
 joined_event("create_return",slot,result);pthread_mutex_unlock(&joined_task_lock);return result;
}
int __wrap_pthread_join(pthread_t handle,void **result_pointer){
 pthread_mutex_lock(&joined_task_lock);size_t slot=joined_task_count;
 for(size_t i=joined_task_count;i>0;i--)if(joined_tasks[i-1].handle_valid&&!joined_tasks[i-1].joined&&pthread_equal(joined_tasks[i-1].handle,handle)){slot=i-1;break;}
 if(slot==joined_task_count)joined_tracking_invalid=1;
 pthread_mutex_unlock(&joined_task_lock);
 /* Delegate unchanged target/output pointer and return EXACTLY its result.
  * No procfs observation, waiting, deadline or result substitution here. */
 int result=__real_pthread_join(handle,result_pointer);
 pthread_mutex_lock(&joined_task_lock);
 if(slot<joined_task_count){joined_tasks[slot].join_result=result;joined_tasks[slot].joined=result==0;joined_event("join_return",slot,result);}
 else {FILE *file=joined_audit();fprintf(file,"{\"event\":\"join_untracked_return\",\"result\":%d}\n",result);joined_audit_close(file);}
 pthread_mutex_unlock(&joined_task_lock);return result;
}
static void joined_refuse(const char *reason){
 FILE *file=joined_audit();fprintf(file,"{\"event\":\"REFUSAL\",\"reason\":\"%s\"}\n",reason);joined_audit_close(file);abort();
}
/* Every row is retained before any refusal; no task is subtracted or ignored. */
static int joined_snapshot(const char *phase){
 struct row{pid_t tid;int read,slot;unsigned long long birth;char raw[4096];}rows[JOINED_TASK_LIMIT];
 DIR *directory=opendir("/proc/self/task");if(!directory)joined_refuse("task-directory-open");
 size_t count=0;int invalid=0,main_seen=0;struct dirent *entry;errno=0;
 while((entry=readdir(directory))){
  if(entry->d_name[0]=='.')continue;if(count==JOINED_TASK_LIMIT){invalid=1;break;}
  struct row *row=&rows[count++];memset(row,0,sizeof(*row));row->slot=-1;row->read=-1;char *end;errno=0;long tid=strtol(entry->d_name,&end,10);
  if(errno||*end||tid<=0){invalid=1;break;}row->tid=(pid_t)tid;row->raw[0]=0;row->birth=0;row->slot=-1;
  row->read=joined_stat(row->tid,row->raw,&row->birth);
  for(size_t i=0;i<joined_task_count;i++)if(joined_tasks[i].started&&joined_tasks[i].tid==row->tid){row->slot=(int)i;break;}
  if(row->tid==getpid()){main_seen=1;if(row->read!=1)invalid=1;}
  else if(row->slot<0)invalid=1;
  else {struct joined_task *task=&joined_tasks[row->slot];if(!task->joined||task->join_result||task->absent||row->read<0||(row->read==1&&row->birth!=task->birth))invalid=1;}
  errno=0;
 }
 if(errno||closedir(directory)||!main_seen)invalid=1;
 FILE *file=joined_audit();fprintf(file,"{\"event\":\"snapshot\",\"phase\":\"%s\",\"literal_threads\":%zu,\"rows\":[",phase,count);
 for(size_t i=0;i<count;i++){if(i)fputc(',',file);struct row *row=&rows[i];fprintf(file,"{\"tid\":%d,\"slot\":%d,\"stat_read\":%d,\"birth\":%llu,\"raw_stat\":",row->tid,row->slot,row->read,row->birth);joined_quote(file,row->raw);fputc('}',file);}
 fprintf(file,"],\"valid\":%s}\n",invalid?"false":"true");joined_audit_close(file);
 if(invalid)joined_refuse("unknown-unjoined-reused-or-malformed-task");return (int)count;
}
static int joined_task_singleton(void){
 pthread_mutex_lock(&joined_task_lock);
 joined_snapshot("initial");
 if(joined_tracking_invalid)joined_refuse("tracking-invalid");
 for(size_t i=0;i<joined_task_count;i++){
  struct joined_task *task=&joined_tasks[i];
  if(!task->created){if(task->started)joined_refuse("failed-create-has-thread");continue;}
  if(!task->started||!task->joined||task->join_result)joined_refuse("missing-positive-join");
  for(;;){
   char path[80],raw[4096]="";struct stat info;unsigned long long birth=0;
   snprintf(path,sizeof(path),"/proc/self/task/%d",task->tid);errno=0;
   if(fstatat(AT_FDCWD,path,&info,AT_SYMLINK_NOFOLLOW)<0){
    if(errno!=ENOENT)joined_refuse("task-directory-observation-error");
    task->absent=1;joined_event("joined_directory_ENOENT",i,ENOENT);break;
   }
   int result=joined_stat(task->tid,raw,&birth);
   FILE *file=joined_audit();fprintf(file,"{\"event\":\"joined_directory_present\",\"slot\":%zu,\"tid\":%d,\"stat_read\":%d,\"birth\":%llu,\"raw_stat\":",i,task->tid,result,birth);joined_quote(file,raw);fputs("}\n",file);joined_audit_close(file);
   if(result<0||(result==1&&birth!=task->birth))joined_refuse("joined-task-birth-changed");
   sched_yield(); /* Wait only for this positively joined exact task. No sleep. */
  }
 }
 int count=joined_snapshot("final");if(count!=1)joined_refuse("final-not-singleton");
 FILE *file=joined_audit();fputs("{\"event\":\"FINAL_SINGLETON\",\"threads\":1}\n",file);joined_audit_close(file);
 pthread_mutex_unlock(&joined_task_lock);return count;
}
