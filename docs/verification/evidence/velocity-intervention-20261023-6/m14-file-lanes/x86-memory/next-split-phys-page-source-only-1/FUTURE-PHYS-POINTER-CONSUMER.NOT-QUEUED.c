/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only exact-original-C/Rust raw adapter fragment. Controlled lower
 * endpoint, never actual physical memory, hash locking or page lifetime proof.
 */
#include <assert.h>
#include <stdint.h>
struct page;
static unsigned calls;static unsigned long seen;static struct page *answer;
struct page *phys_to_page(uintptr_t phys){++calls;seen=phys;return answer;}
#include "EXACT-ORIGINAL-C-PROVIDER.inc"
extern void *rust_phys(unsigned long) __asm__("x86_split_phys_to_page_bridge");
static void future_phys_case(unsigned long phys,struct page *result){
 answer=result;calls=0;void*a=x86_split_phys_to_page_bridge(phys);assert(calls==1 && seen==phys && a==(void*)answer);
 calls=0;void*b=rust_phys(phys);assert(calls==1 && seen==phys && b==a);
}
/* Actual saved Rust adapter uses its existing foreign phys_to_page declaration.
 * Alias original C static symbol only; full-width physical values and NULL/real
 * aligned observer-owned page/sentinel results test transport without dereference.
 * No invented Page alignment/range validation or NULL rejection. No new queue.
 * A deeper lookup test must reuse real Rust phys_to_page_lookup_body_result
 * with actual C geometry/lock providers; lower C phys_to_page remains debt.
 */
