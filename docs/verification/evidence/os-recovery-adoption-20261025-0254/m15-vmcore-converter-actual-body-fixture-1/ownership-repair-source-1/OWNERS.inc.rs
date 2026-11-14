// Project-owned temporary allocations are scoped to their live users.
#[cfg(ldump2_full_body)]
struct OwnedAllocation(*mut c_void);

#[cfg(ldump2_full_body)]
impl OwnedAllocation {
    unsafe fn allocate(size: usize) -> Self { Self(malloc(size)) }
    fn as_ptr(&self) -> *mut c_void { self.0 }
}

#[cfg(ldump2_full_body)]
impl Drop for OwnedAllocation {
    fn drop(&mut self) {
        if !self.0.is_null() {
            unsafe { free(core::mem::replace(&mut self.0, null_mut())); }
        }
    }
}

// BFD borrows names until terminal teardown. Private prefixes own these blocks;
// no public dump layout or allocator boundary changes.
#[repr(C)]
#[cfg(ldump2_full_body)]
struct OwnedSectionName { next: *mut OwnedSectionName, bytes: [c_char; PHYSMEM_NAME_SIZE] }

#[cfg(ldump2_full_body)]
struct OwnedSectionNames { head: *mut OwnedSectionName }

#[cfg(ldump2_full_body)]
impl OwnedSectionNames {
    fn new() -> Self { Self { head: null_mut() } }
    unsafe fn allocate(&mut self) -> *mut c_char {
        let item = malloc(size_of::<OwnedSectionName>()).cast::<OwnedSectionName>();
        if item.is_null() { return null_mut(); }
        (*item).next = self.head;
        self.head = item;
        addr_of_mut!((*item).bytes).cast::<c_char>()
    }
}

#[cfg(ldump2_full_body)]
impl Drop for OwnedSectionNames {
    fn drop(&mut self) {
        unsafe {
            while !self.head.is_null() {
                let item = self.head;
                self.head = (*item).next;
                free(item.cast::<c_void>());
            }
        }
    }
}

#[cfg(ldump2_full_body)]
struct OwnedBfd { handle: *mut Bfd }

#[cfg(ldump2_full_body)]
impl OwnedBfd {
    unsafe fn finish(&mut self) -> c_int {
        // Selected bfd_close consumes the handle even on FALSE. Disarm first.
        bfd_close(core::mem::replace(&mut self.handle, null_mut()))
    }
}

#[cfg(ldump2_full_body)]
impl Drop for OwnedBfd {
    fn drop(&mut self) {
        if !self.handle.is_null() {
            // Earlier errors do not finalize pending output. Selected
            // close_all_done unconditionally deletes BFD, including FALSE.
            unsafe { let _ = bfd_close_all_done(core::mem::replace(&mut self.handle, null_mut())); }
        }
    }
}

