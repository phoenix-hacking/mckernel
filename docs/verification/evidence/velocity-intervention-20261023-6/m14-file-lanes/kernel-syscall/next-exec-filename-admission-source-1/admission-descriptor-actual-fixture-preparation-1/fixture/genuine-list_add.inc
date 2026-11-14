#[inline(always)]
unsafe fn list_add(new: *mut AbiListHead, prev: *mut AbiListHead, next: *mut AbiListHead) {
    (*next).prev = new;
    (*new).next = next;
    (*new).prev = prev;
    (*prev).next = new;
}
