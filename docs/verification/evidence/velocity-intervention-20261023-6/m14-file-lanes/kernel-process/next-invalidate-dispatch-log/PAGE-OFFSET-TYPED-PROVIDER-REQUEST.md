Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

F01 page-owner request: provide a typed Rust accessor for the existing
kernel/rust/page_helpers.rs::Page offset, returning OffT without a new ownership
action. Suggested interface, subject to the owning module's naming:

    pub unsafe extern "C" fn page_get_offset(page: *const Page) -> OffT

The retained actual process C callback is:

    long process_page_offset_bridge(void *page)
    {
        return ((struct page *)page)->offset;
    }

This is one ordinary signed off_t field read. It returns negative and positive
offsets unchanged, has no NULL policy, allocation, lock, refcount, mutation,
logging or release. Existing Page is repr(C), with private offset: OffT; the
module already asserts its layout. Process code must not guess its offset.

The exact existing Rust consumer is process_invalidate_one_page_body_result in
kernel/rust/process_helpers.rs. After the existing phys_to_page(phys) callback,
it computes the range's linear offset. Only for a non-NULL borrowed Page does
it call page_offset(page). If that value differs from the linear offset, it
encodes the Page's offset into local apte. This precedes PTE exchange, the TLB
callback and page_unmap. The synchronous enclosing invalidate visit retains
its existing page-table lock and memobj reference. The adapter must not add a
Page reference or access it after unmap/release.

The currently selected getter is the C callback above. Its field is private
inside the typed Rust Page module, so process_helpers cannot replace that C
field access through a typed call today. A page-owned accessor would let
process_helpers provide the same callback by casting its borrowed opaque
pointer to the existing Page type, without shared-header changes or a C getter.

Requested next observation: actual C getter versus the page-owned Rust accessor
for signed offset extremes, typed Page/layout ABI and the unchanged process
consumer's pre-exchange/pre-unmap call order. No execution grant or
provider/default/native acceptance is supplied by this source request.
