#[inline(always)]
unsafe fn list_add_after(new: *mut AbiListHead, head: *mut AbiListHead) {
    list_add(new, head, (*head).next);
}
