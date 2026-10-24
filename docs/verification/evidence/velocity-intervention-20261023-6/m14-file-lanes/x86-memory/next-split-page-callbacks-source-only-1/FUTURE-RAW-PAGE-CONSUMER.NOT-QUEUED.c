/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only controlled endpoint fragment. Does not dereference page sentinels.
 */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
static void *seen;static unsigned calls;static int endpoint_ret;
void page_map(void *page) { ++calls;seen=page; }
int page_unmap(void *page) { ++calls;seen=page;return endpoint_ret; }
#include "EXACT-ORIGINAL-C-PROVIDERS.inc"
extern void rust_map(void*) __asm__("x86_split_page_map_bridge");
extern int rust_unmap(void*) __asm__("x86_split_page_unmap_bridge");
static void future_page_case(void *page,int ret) {
 calls=0;seen=0;x86_split_page_map_bridge(page);assert(calls==1 && seen==page);
 calls=0;seen=0;rust_map(page);assert(calls==1 && seen==page);
 endpoint_ret=ret;calls=0;seen=0;int a=x86_split_page_unmap_bridge(page);
 assert(calls==1 && seen==page && a==ret);
 calls=0;seen=0;int b=rust_unmap(page);assert(calls==1 && seen==page && b==a);
}
/* Future exact extracted Rust bodies use mock crate::page_helpers::page_map and
 * page_unmap shims calling these actual C endpoints. Alias the two original
 * static definitions to original_C_* assembler names only; preserve body bytes.
 * Valid aligned object and controlled sentinel bit patterns (including NULL)
 * establish unchanged transport/no added null policy ONLY. Real production
 * page helpers require their existing lifetime/lock/page ownership contract;
 * sentinel vectors never enter actual page helpers. Test CInt0/1/-1/min/max.
 * No refcount/hashlock/free/real page mapping, native or partial-link credit.
 */
