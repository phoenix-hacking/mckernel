/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Wrapper-only downstream recorder: explicitly does not prove actual freeing,
 * allocator locks, tracking/accounting, or physical-page ownership. The existing
 * full Rust _ihk_mc_free_pages remains the real production provider.
 * Link the exact Rust wrapper and source-derived metadata into a future isolated
 * observer (its other support modules must not also define this recorder symbol).
 */
#include <assert.h>
#include <string.h>
extern void x86_pt_free_pages_bridge(void *, int);
extern const char x86_pt_free_pages_file[];
extern const int x86_pt_free_pages_line, x86_pt_free_pages_flag;
static struct { void *ptr; int pages, flag; char *file; int line; } seen;
static unsigned calls;
void _ihk_mc_free_pages(void *ptr,int pages,int flag,char *file,int line)
{
    ++calls;
    seen.ptr=ptr; seen.pages=pages; seen.flag=flag; seen.file=file; seen.line=line;
}
static void future_forwarding_case(void *ptr, int pages)
{
    unsigned before=calls;
    x86_pt_free_pages_bridge(ptr,pages);
    assert(calls==before+1 && seen.ptr==ptr && seen.pages==pages);
    assert(seen.flag==x86_pt_free_pages_flag && seen.flag==0);
    assert(seen.file==x86_pt_free_pages_file && seen.line==807);
    assert(x86_pt_free_pages_line==807);
}
/* Also extract original C provider using its numeric source-line anchor and
 * same C filename; compare recorder events for original and Rust. No free occurs
 * in this observer, so negative/zero count bit-forwarding is not allocator input
 * qualification. Real allocator/provider-chain proof requires the full current
 * crate/selected TU/partial link and its already-established allocator contracts.
 */
