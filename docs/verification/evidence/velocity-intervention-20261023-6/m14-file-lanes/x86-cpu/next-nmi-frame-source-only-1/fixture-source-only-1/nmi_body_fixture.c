/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY. No main/launcher/profile: no second executable cohort.
 * The actual frame algorithms are compared separately from flags capture.
 */
#include <ihk/context.h>
typedef void(*Entry)();
typedef void(*Rewrite)(void*,Entry);
extern void original_mod_nmi_pure(void*,Entry);
extern void rust_mod_nmi_pure(void*,Entry);
extern void original_mod_nmi_raw(void*,Entry);
extern void rust_mod_nmi_raw(void*,Entry);
enum { WORDS=sizeof(ihk_mc_user_context_t)/sizeof(unsigned long), PREFIX=2, SUFFIX=2 };
union RealContextStorage { ihk_mc_user_context_t context;unsigned long words[WORDS]; };
struct GuardedContext { unsigned long before[PREFIX];union RealContextStorage live;unsigned long after[SUFFIX]; };
_Static_assert(WORDS==28,"use actual header context storage, not invented27word frame");
_Static_assert(__builtin_offsetof(struct GuardedContext,live)==2*sizeof(unsigned long),"aligned actual storage");
static unsigned long captured_flags,initial[WORDS],captured_input[WORDS];
static unsigned long *active_words;
static unsigned capture_count,sentinel_calls,capture_mutation;
static int failed;
static void require(int b){if(!b)failed=1;}
static void sentinel_a(void){sentinel_calls++;}
static void sentinel_b(void){sentinel_calls++;}
unsigned long fixture_nmi_capture_flags(void){
 require(active_words!=0&&capture_count==0);capture_count++;
 for(unsigned i=0;i<WORDS;i++)require(active_words[i]==initial[i]);
 /* Deliberate capture-boundary mutation checks copy reads occur aftercapture.
  * This is a controlled pure boundary, not a simulated CPUflag instruction. */
 if(capture_mutation)active_words[26]^=0xd0c0b0a090807060UL;
 for(unsigned i=0;i<WORDS;i++)captured_input[i]=active_words[i];
 return captured_flags;
}
static unsigned long pattern(unsigned i,unsigned seed){
 return (0x9e3779b97f4a7c15UL*(i+1+seed*29))^((unsigned long)seed<<47)^i;
}
static void initialize(struct GuardedContext *g,unsigned seed){
 for(unsigned i=0;i<PREFIX;i++)g->before[i]=0x1020304050607080UL+i;
 for(unsigned i=0;i<WORDS;i++)g->live.words[i]=pattern(i,seed);
 for(unsigned i=0;i<SUFFIX;i++)g->after[i]=0xfedcba9876543210UL+i;
}
static void check_guards(struct GuardedContext*g){
 for(unsigned i=0;i<PREFIX;i++)require(g->before[i]==0x1020304050607080UL+i);
 for(unsigned i=0;i<SUFFIX;i++)require(g->after[i]==0xfedcba9876543210UL+i);
}
static void run_pure(Rewrite fn,struct GuardedContext*g,Entry entry,unsigned long flags,unsigned mutate){
 active_words=g->live.words;capture_count=0;capture_mutation=mutate;captured_flags=flags;
 for(unsigned i=0;i<WORDS;i++)initial[i]=active_words[i];
 fn(active_words,entry);require(capture_count==1&&sentinel_calls==0);
 /* Oracle reads an immutable postcapture snapshot. It is not a second
  * overlapping-copy loop and exposes reverse/memcpy-style overlap errors. */
 for(unsigned i=0;i<22;i++)require(active_words[i]==captured_input[i+5]);
 require(active_words[22]==(unsigned long)entry);
 require(active_words[23]==0x20&&active_words[24]==(flags&~(unsigned long)RFLAGS_IF));
 require(active_words[25]==(unsigned long)(active_words+27)&&active_words[26]==0x28);
 require(active_words[27]==captured_input[27]);check_guards(g);active_words=0;
}
int m14_nmi_pure_body_fixture(unsigned long *pairs_out){
 unsigned long flags[136]={0,1,~0UL,1UL<<63,(1UL<<63)-1,0x200UL,0x202UL,0x246UL};unsigned n=8;
 for(unsigned b=0;b<64;b++){flags[n++]=1UL<<b;flags[n++]=~(1UL<<b);}
 Entry entries[3]={0,sentinel_a,sentinel_b};unsigned long pairs=0;failed=0;sentinel_calls=0;
 for(unsigned f=0;f<n;f++)for(unsigned seed=0;seed<8;seed++)for(unsigned e=0;e<3;e++)for(unsigned m=0;m<2;m++){
  struct GuardedContext a,b;initialize(&a,seed);initialize(&b,seed);
  run_pure(original_mod_nmi_pure,&a,entries[e],flags[f],m);
  run_pure(rust_mod_nmi_pure,&b,entries[e],flags[f],m);
  for(unsigned i=0;i<WORDS;i++)if(i!=25)require(a.live.words[i]==b.live.words[i]);
  /* Stack addresses differ: each producer must name its own base+27. */
  require(a.live.words[25]-(unsigned long)a.live.words==27*sizeof(unsigned long));
  require(b.live.words[25]-(unsigned long)b.live.words==27*sizeof(unsigned long));pairs++;
 }
 if(pairs_out)*pairs_out=pairs;return failed?1:0;
}
struct M14RawNmiObservation { unsigned long original_flags_masked,Rust_flags_masked;unsigned structural_equal;unsigned IF_cleared; };
int m14_nmi_raw_body_fixture_SOURCE_ONLY_NOT_RELEASED(struct M14RawNmiObservation*out){
 /* No unqualified byte-equality test for flags: C/Rustcompilerprologues can
  * change flags before their respective captureinstruction. Never execute
  * the returned selector/returnframe or infer kernelCS from userspace. */
 struct GuardedContext a,b;unsigned long before[WORDS];failed=0;sentinel_calls=0;
 initialize(&a,3);initialize(&b,3);for(unsigned i=0;i<WORDS;i++)before[i]=a.live.words[i];
 original_mod_nmi_raw(a.live.words,sentinel_a);rust_mod_nmi_raw(b.live.words,sentinel_a);
 for(unsigned i=0;i<22;i++){require(a.live.words[i]==before[i+5]);require(b.live.words[i]==before[i+5]);}
 for(unsigned which=0;which<2;which++){
  struct GuardedContext*g=which?&b:&a;unsigned long*w=g->live.words;
  require(w[22]==(unsigned long)sentinel_a&&w[23]==0x20&&w[26]==0x28);
  require(w[25]==(unsigned long)(w+27)&&w[27]==before[27]&&(w[24]&RFLAGS_IF)==0);check_guards(g);
 }
 require(sentinel_calls==0);
 if(out){out->original_flags_masked=a.live.words[24];out->Rust_flags_masked=b.live.words[24];out->structural_equal=failed==0;out->IF_cleared=((a.live.words[24]|b.live.words[24])&RFLAGS_IF)==0;}
 return failed?1:0;
}
