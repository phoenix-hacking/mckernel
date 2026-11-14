/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only original-C/Rust adapter fragment. This controlled endpoint scope
 * does not prove enabled accounting or atomic updates; actual mem_helpers owns
 * rusage conversion, atomic signed adds/negation and enable_rusage gating.
 */
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
static unsigned calls;static unsigned long seen_size;static int seen_pgsize,seen_op;
void memory_stat_rss_add(unsigned long size,int pgsize){++calls;seen_op=1;seen_size=size;seen_pgsize=pgsize;}
void memory_stat_rss_sub(unsigned long size,int pgsize){++calls;seen_op=-1;seen_size=size;seen_pgsize=pgsize;}
#include "EXACT-ORIGINAL-C-PROVIDERS.inc"
extern void rust_add(size_t,size_t) __asm__("x86_split_rss_add_bridge");
extern void rust_sub(size_t,size_t) __asm__("x86_split_rss_sub_bridge");
static void future_rss_case(size_t size,size_t pgsize,int subtract){
 calls=0;if(subtract)x86_split_rss_sub_bridge(size,pgsize);else x86_split_rss_add_bridge(size,pgsize);
 assert(calls==1);unsigned long s=seen_size;int p=seen_pgsize,op=seen_op;
 calls=0;if(subtract)rust_sub(size,pgsize);else rust_add(size,pgsize);
 assert(calls==1 && seen_size==s && seen_pgsize==p && seen_op==op);
}
/* Full-width sizes and pgsize including0,4096,2MiB,1GiB,INT_MAX,INT_MAX+1,
 * UINT_MAX,1UL<<32,1UL<<63,SIZE_MAX distinguish original size_t->int narrowing.
 * Keep exact original callback body and use assembler aliases only; new Rust
 * wrappers are exact saved bodies with controlled mem_helpers endpoint shims.
 * Later real accounting fixture must reuse actual Rust add/sub + RUSAGE layout,
 * rusage_pgsize_to_pgtype and atomic helper in both cfgs. No current run/queue.
 */
