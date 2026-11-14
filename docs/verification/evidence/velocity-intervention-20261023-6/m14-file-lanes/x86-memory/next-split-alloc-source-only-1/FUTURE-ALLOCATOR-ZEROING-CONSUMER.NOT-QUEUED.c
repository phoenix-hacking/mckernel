/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source fragment only; exact original helpers and actual Rust zeroing reused.
 */
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
struct page_table { unsigned long entries[512]; };
typedef unsigned long ihk_mc_ap_flag;
static struct page_table memory[2];
static unsigned calls;static int seen_count,seen_flags,mode;
void *x86_pt_alloc_pages_bridge(int n,int f) {
 ++calls;seen_count=n;seen_flags=f;
 return mode<0?NULL:&memory[mode];
}
extern void *x86_pt_alloc_zeroed_result(int,void *(*)(int,int));
#include "EXACT-ORIGINAL-C-HELPER.inc"
#include "EXACT-ORIGINAL-C-PROVIDER.inc"
extern void *rust_split_alloc(int,int) __asm__("x86_split_alloc_new_pt_bridge");
static void future_split_alloc_case(int count,int flags,int result_mode) {
 mode=result_mode;calls=0;seen_count=seen_flags=0;
 memset(memory,0xa5,sizeof(memory));
 void *a=x86_split_alloc_new_pt_bridge(count,flags);
 unsigned want_calls=calls;int want_n=seen_count,want_f=seen_flags;
 unsigned char expected[sizeof(memory)];memcpy(expected,memory,sizeof(memory));
 calls=0;seen_count=seen_flags=0;memset(memory,0xa5,sizeof(memory));
 void *b=rust_split_alloc(count,flags);
 assert(a==b && calls==want_calls && seen_count==want_n && seen_flags==want_f);
 assert(!memcmp(expected,memory,sizeof(memory)));
 assert(calls==(count==1?1U:0U));
 if(count==1) {
  assert(seen_count==1 && seen_flags==flags);
  if(mode>=0) for(unsigned i=0;i<512;i++)assert(memory[mode].entries[i]==0);
 } else assert(a==NULL);
}
/* Counts INT_MIN,-2,-1,0,1,2,3,512,INT_MAX; original signed flags and NULL/two
 * actual aligned static buffers. Extract exact saved Rust wrapper+zeroing helper
 * into the future Rust fixture, retain PT_ENTRIES=512/write_bytes actual source.
 * Original static symbol must use an assembler alias original_C_split_alloc;
 * Rust symbol uses its existing public name. No body rewriting beyond alias.
 * This proves only gated callback/zeroing behavior, not real allocation failure
 * policy, page ownership publication, TLB effects or native split execution.
 */
