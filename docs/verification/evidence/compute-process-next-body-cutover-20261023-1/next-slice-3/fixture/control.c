/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact existing dynamic-debug descriptor ABI/control operation; hosted sink. */
#include <ihk/debug.h>
extern void leaf_fail(unsigned);
#define CHECK(x) do { if(!(x))leaf_fail(__LINE__); } while(0)
extern struct ddebug process_sched_migrate_debug;
extern struct ddebug __start___verbose[],__stop___verbose[];
extern const unsigned long LEAF_DEBUG_LAYOUT[6];
extern void leaf_set_ddebug_flags(struct ddebug *,unsigned int);
extern void leaf_original_migrate_log(unsigned long,int,int);
extern void leaf_actual_migrate_log(unsigned long,int,int) __asm__("process_sched_migrate_log_bridge");
extern int leaf_printf_count,leaf_expected_tid,leaf_expected_cpu,leaf_eval_count,leaf_return_value;
extern char leaf_text[160];
static int same(const char *a,const char *b) { while(*a&&*a==*b){a++;b++;}return *a==*b; }
static unsigned long eval_thread(unsigned long a) { leaf_eval_count++;return a; }
static int eval_int(int a) { leaf_eval_count++;return a; }
static void zero(void *p,unsigned long n) { unsigned char *b=p;while(n--)*b++=0; }
static struct ddebug *original_descriptor(void) {
 struct ddebug *found=0;unsigned n=0;
 for(struct ddebug *p=__start___verbose;p<__stop___verbose;p++) {
  if(p!=&process_sched_migrate_debug&&same(p->func,"process_sched_migrate_log_bridge")){found=p;n++;}
 }
 CHECK(n==1);return found;
}
static unsigned int word(const struct ddebug *p) {
 const unsigned char *b=(const unsigned char *)p+LEAF_DEBUG_LAYOUT[5];
 return (unsigned int)b[0]|((unsigned int)b[1]<<8)|((unsigned int)b[2]<<16)|((unsigned int)b[3]<<24);
}
struct result { int calls,evals;char text[160]; };
static struct result run(int rust,unsigned int flags,unsigned long thread,int tid,int cpu,struct ddebug *original) {
 leaf_printf_count=leaf_eval_count=0;leaf_expected_tid=tid;leaf_expected_cpu=cpu;zero(leaf_text,sizeof(leaf_text));
 struct ddebug *descriptor=rust?&process_sched_migrate_debug:original;
 leaf_set_ddebug_flags(descriptor,flags);CHECK(descriptor->flags==flags&&descriptor->line==422&&word(descriptor)==(422|(flags<<24)));
 if(rust)leaf_actual_migrate_log(eval_thread(thread),eval_int(tid),eval_int(cpu));
 else leaf_original_migrate_log(eval_thread(thread),eval_int(tid),eval_int(cpu));
 CHECK(leaf_eval_count==3&&leaf_printf_count==(flags!=0));
 CHECK(descriptor->flags==flags&&descriptor->line==422&&word(descriptor)==(422|(flags<<24)));
 struct result r;zero(&r,sizeof(r));r.calls=leaf_printf_count;r.evals=leaf_eval_count;
 for(unsigned i=0;i<sizeof(r.text);i++) { r.text[i]=leaf_text[i]; }
 return r;
}
unsigned long leaf_run_cases(void) {
 struct ddebug *original=original_descriptor();struct ddebug *actual=&process_sched_migrate_debug;
 const unsigned long layout[]={sizeof(struct ddebug),__alignof__(struct ddebug),__builtin_offsetof(struct ddebug,file),__builtin_offsetof(struct ddebug,func),__builtin_offsetof(struct ddebug,fmt),__builtin_offsetof(struct ddebug,fmt)+sizeof(actual->fmt)};
 for(unsigned i=0;i<6;i++)CHECK(layout[i]==LEAF_DEBUG_LAYOUT[i]);
 CHECK(!original->flags&&!actual->flags&&original->line==422&&actual->line==422&&!original->fmt&&!actual->fmt);
 CHECK(same(original->file,"/src/kernel/process.c")&&same(original->file,actual->file)&&same(original->func,actual->func));
 const int boundary[]={0,1,-1,(-2147483647-1),2147483647};
 const unsigned long pointers[]={0,1,~0UL,1UL<<63,0x123456789abcdef0UL};unsigned long n=0;
 for(unsigned int flags=0;flags<256;flags++)for(unsigned t=0;t<5;t++)for(unsigned c=0;c<5;c++)for(unsigned p=0;p<5;p++) {
  leaf_return_value=boundary[flags%5];struct result a=run(0,flags,pointers[p],boundary[t],boundary[c],original),b=run(1,flags,pointers[p],boundary[t],boundary[c],original);
  const unsigned char *x=(const unsigned char *)&a,*y=(const unsigned char *)&b;
  for(unsigned long i=0;i<sizeof(a);i++) { CHECK(x[i]==y[i]); }
  n++;
 }
 return n;
}
