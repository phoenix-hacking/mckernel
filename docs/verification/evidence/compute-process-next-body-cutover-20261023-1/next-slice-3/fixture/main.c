/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stdio.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
struct ddebug;
extern void leaf_original_migrate_log(unsigned long,int,int);
extern void leaf_actual_migrate_log(unsigned long,int,int) __asm__("process_sched_migrate_log_bridge");
extern void leaf_set_ddebug_flags(struct ddebug *,unsigned int);
extern unsigned long leaf_run_cases(void);
int leaf_printf_count,leaf_expected_tid,leaf_expected_cpu,leaf_eval_count,leaf_return_value;
char leaf_text[160];
int kprintf(const char *fmt,...) {
 va_list a;va_start(a,fmt);const char *name=va_arg(a,const char *);int tid=va_arg(a,int),cpu=va_arg(a,int);va_end(a);
 if(strcmp(fmt,"%s: tid: %d -> cpu: %d\n")||strcmp(name,"sched_request_migrate")||tid!=leaf_expected_tid||cpu!=leaf_expected_cpu) { abort(); }
 if(leaf_eval_count!=3) { abort(); }
 leaf_printf_count++;
 snprintf(leaf_text,sizeof(leaf_text),fmt,name,tid,cpu);return leaf_return_value;
}
void leaf_fail(unsigned line) { fprintf(stderr,"assertion line=%u\n",line);exit(1); }
int main(void) { unsigned long n=leaf_run_cases();if(n!=32000) { return 2; }
 printf("PASS pairs=%lu flags=256 real_descriptor_layout_words=6 original_macro_and_actual_Rust; no kernel state execution\n",n);return 0; }
