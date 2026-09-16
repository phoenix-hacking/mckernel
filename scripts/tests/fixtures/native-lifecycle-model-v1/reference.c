/* MODEL_ONLY: independently implemented bounded lifecycle table. */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_OBJECTS 8
#define MAX_OPS 128
#define MAX_EVENTS 256
enum phase { EMPTY, ALLOCATED, BORN, RUNNABLE, ABORTED, THREAD_TERMINAL, RETIRE_BEGUN, THREAD_RETIRED };
struct object { enum phase phase; uint64_t capture,generation,application,process,thread,exec; uint32_t slot,refs; int32_t pid,tid; int process_terminal,process_retired,main_storage,zombie,vm_owned; };
struct model { struct object object[MAX_OBJECTS]; uint64_t capacity,attempts,lost,operations; int incomplete,ended; };

static int find(struct model *m,uint64_t process,uint64_t thread) { for(int i=0;i<MAX_OBJECTS;i++) if(m->object[i].phase!=EMPTY&&m->object[i].process==process&&(thread==0||m->object[i].thread==thread)) return i; return -1; }
static void emit(struct model *m,const char *kind,uint64_t process,uint64_t thread,uint64_t raw,uint64_t branch) {
 if(m->attempts==UINT64_MAX){m->incomplete=1;m->lost=UINT64_MAX;return;} m->attempts++;
 if(m->attempts<=m->capacity) printf("E %"PRIu64" %s %"PRIu64" %"PRIu64" %"PRIu64" %"PRIu64"\n",m->attempts,kind,process,thread,raw,branch);
 else {m->incomplete=1;if(m->lost!=UINT64_MAX)m->lost++;}
}
static unsigned apply(struct model *m,char *op,uint64_t n[9]) {
 if(++m->operations>MAX_OPS){m->incomplete=1;return 15;} if(m->ended){m->incomplete=1;return 14;}
 uint64_t process=n[1],thread=n[2];
 if(!strcmp(op,"alloc")){
  uint64_t capture=n[1],slot=n[2],generation=n[3],application=n[4],proc=n[5],thr=n[6],pid=n[7],tid=n[8],exec=application;
  if(!capture||slot>=64||!generation||!application||!proc||!thr||!pid){m->incomplete=1;return 1;}
  if(find(m,proc,thr)>=0){m->incomplete=1;return 2;} for(int j=0;j<MAX_OBJECTS;j++)if(m->object[j].phase!=EMPTY&&m->object[j].phase!=THREAD_RETIRED&&tid&&m->object[j].tid==(int32_t)tid){m->incomplete=1;return 2;}
  int i;for(i=0;i<MAX_OBJECTS&&m->object[i].phase!=EMPTY;i++);if(i==MAX_OBJECTS){m->incomplete=1;return 9;}
  m->object[i]=(struct object){ALLOCATED,capture,generation,application,proc,thr,exec,(uint32_t)slot,1,(int32_t)pid,(int32_t)tid,0,0,1,0,1};emit(m,"ALLOC",proc,thr,0,0);return 0;
 }
 if(!strcmp(op,"capture_end")){m->ended=1;emit(m,"CAPTURE_END",0,0,0,0);for(int i=0;i<MAX_OBJECTS;i++)if(m->object[i].phase!=EMPTY&&(!m->object[i].process_retired||m->object[i].phase!=THREAD_RETIRED))m->incomplete=1;return 0;}
 if(!strcmp(op,"launcher_loss")){emit(m,"LAUNCHER_LOSS",0,0,0,0);return 0;}
 int i=find(m,process,thread);if(i<0){m->incomplete=1;return 1;}struct object *x=&m->object[i];
#define EVENT(k,r,b) do { emit(m,k,process,thread,r,b); } while(0)
 if(!strcmp(op,"birth")){if(x->phase!=ALLOCATED)return 2;x->phase=BORN;EVENT("BIRTH",0,0);return 0;}
 if(!strcmp(op,"runnable")){if(x->phase!=BORN)return 3;x->phase=RUNNABLE;EVENT("RUNNABLE",0,0);return 0;}
 if(!strcmp(op,"abort")){if(x->phase!=ALLOCATED)return 3;x->phase=ABORTED;EVENT("ABORT",n[3],0);return 0;}
 if(!strcmp(op,"add_ref")){if(x->phase==THREAD_RETIRED||x->refs==UINT32_MAX)return 7;x->refs++;return 0;}
 if(!strcmp(op,"drop_ref")){if(!x->refs)return 4;x->refs--;return 0;}
 if(!strcmp(op,"thread_terminal")){if(x->phase!=BORN&&x->phase!=RUNNABLE)return 2;x->phase=THREAD_TERMINAL;EVENT("THREAD_TERMINAL",n[3],n[6]);return 0;}
 if(!strcmp(op,"process_terminal")){if(x->process_terminal||x->phase==ALLOCATED||x->phase==ABORTED)return 2;x->process_terminal=1;EVENT("PROCESS_TERMINAL",n[3],n[6]);return 0;}
 if(!strcmp(op,"retire_begin")){if((x->refs==0&&(x->phase==THREAD_TERMINAL||x->phase==ABORTED))||(n[3]==1&&x->phase==ABORTED)){x->phase=RETIRE_BEGUN;EVENT("RETIRE_BEGIN",0,n[3]==1);return 0;}return 4;}
 if(!strcmp(op,"thread_retire")){if(x->phase!=RETIRE_BEGUN)return 5;x->phase=THREAD_RETIRED;EVENT("THREAD_RETIRE",0,0);return 0;}
 if(!strcmp(op,"release_main")){x->main_storage=x->vm_owned=0;return 0;}
 if(!strcmp(op,"set_zombie")){x->zombie=1;return 0;}if(!strcmp(op,"clear_zombie")){x->zombie=0;return 0;}
 if(!strcmp(op,"process_retire")){if(x->phase==THREAD_RETIRED&&!x->main_storage&&!x->zombie&&!x->vm_owned){x->process_retired=1;EVENT("PROCESS_RETIRE",0,!x->process_terminal);return 0;}return 8;}
 return 1;
}
int main(void){struct model m={0};char head[32];uint64_t cap;if(scanf("%31s %"SCNu64,head,&cap)!=2||strcmp(head,"MODEL1")||cap>MAX_EVENTS)return 2;m.capacity=cap;
 char op[32];uint64_t n[9];while(scanf("%31s",op)==1){for(int i=0;i<9;i++)if(scanf("%"SCNu64,&n[i])!=1)return 2;unsigned result=apply(&m,op,n);printf("R %"PRIu64" %"PRIu64" %u\n",m.operations,n[0],result);for(int i=0;i<MAX_OBJECTS;i++){struct object*x=&m.object[i];if(x->phase!=EMPTY)printf("S %"PRIu64" %u %"PRIu64" %"PRIu64" %"PRIu64" %"PRIu64" %"PRIu64" %d %d %u %d\n",x->capture,x->slot,x->generation,x->application,x->process,x->thread,x->exec,x->pid,x->tid,x->refs,x->phase);}}
 printf("Z %d %"PRIu64" %"PRIu64"\n",m.ended&&!m.incomplete,m.lost,m.attempts);return 0;}
