/* Observation callbacks only: these NEVER implement or claim actual IHK
 * operations. They consume borrowed inputs synchronously using genuine libc;
 * no device, ioctl, backend or installed provider is invoked. */
#define TRACKER_POISON_FREE_ERRNO
#include "allocator_tracker.h"
typedef int (*string_callback)(int,char *,char *);
extern int fixture_first(int,const char *,int,string_callback);
static const char *expected_text, *default_pointer;
static int expected_owned, expected_key, expected_integer, callback_result, callback_calls, callback_ok;
static int is_owned(const void *p) { for(int i=0;i<32;i++) if(owned[i]==p) return 1; return 0; }
static void consume_string(const char *value) {
 ++callback_calls;
 if(!value || strcmp(value,expected_text) || is_owned(value)!=expected_owned ||
    (!expected_owned && value!=default_pointer)) { callback_ok=0; return; }
 /* This independent copy is the callback's only owned allocation. The borrowed
  * input must remain live after freeing the copy and until callback return. */
 char *copy=__wrap_strdup(value);
 if(!copy) abort();
 if(strcmp(copy,expected_text)) callback_ok=0;
 __wrap_free(copy);
 if(strcmp(value,expected_text) || (expected_owned && !is_owned(value))) callback_ok=0;
}
static int observe_string(int index,char *value,char *error) {
 if(index!=0 || error) callback_ok=0;
 consume_string(value); errno=ERANGE; return callback_result;
}
int observe_kargs(int index,char *value) {
 if(index!=0) callback_ok=0;
 consume_string(value); errno=ERANGE; return callback_result;
}
int observe_conf(int index,int key,void *value) {
 int supplied;
 ++callback_calls;
 if(!value) { callback_ok=0; errno=ERANGE; return callback_result; }
 memcpy(&supplied,value,sizeof(supplied));
 if(index!=0 || key!=expected_key || supplied!=expected_integer) callback_ok=0;
 errno=ERANGE; return callback_result;
}
static void begin(const char *text,int owned_value,int result) {
 expected_text=text; expected_owned=owned_value; callback_result=result;
 callback_calls=0; callback_ok=1; reset(0);
}
static void end(const char *label,int result) {
 int observed_errno=errno, observed_live=live, reclaimed=discard();
 int ok=result==callback_result && callback_ok && callback_calls==1 && observed_live==0 && reclaimed==0 && observed_errno==ERANGE;
 ++checks; if(!ok) ++failures;
 printf("%s result=%d callback-calls=%d borrow-ok=%d live=%d reclaimed=%d errno=%d ok=%d\n",
        label,result,callback_calls,callback_ok,observed_live,reclaimed,observed_errno,ok);
}
int run_callback_consumer(void) {
 begin("first",1,0);
 end("first-success",fixture_first(0,"IHK_CPUS=first\0IHK_CPUS=second",2,observe_string));
 begin("first",1,-33);
 end("first-error",fixture_first(0,"IHK_CPUS=first",1,observe_string));
 expected_key=5; expected_integer=30; begin(NULL,0,0);
 end("config-setter-success",ihk_reserve_mem_conf_str(0,"IHK_RESERVE_MEM_TIMEOUT=30",1));
 expected_key=5; expected_integer=40; begin(NULL,0,-34);
 end("config-setter-error",ihk_reserve_mem_conf_str(0,"IHK_RESERVE_MEM_TIMEOUT=40",1));
 default_pointer="hidos default";
 begin("hidos first",1,0);
 end("kargs-selected-success",ihk_os_kargs_str(0,"IHK_KARGS=hidos first\0IHK_KARGS=hidos second",2,default_pointer));
 begin("hidos fail",1,-35);
 end("kargs-selected-error",ihk_os_kargs_str(0,"IHK_KARGS=hidos fail",1,default_pointer));
 begin(default_pointer,0,0);
 end("kargs-default-success",ihk_os_kargs_str(0,"OTHER=x",1,default_pointer));
 printf("callback candidate checks=%d failures=%d\n",checks,failures);
 return failures?1:0;
}
