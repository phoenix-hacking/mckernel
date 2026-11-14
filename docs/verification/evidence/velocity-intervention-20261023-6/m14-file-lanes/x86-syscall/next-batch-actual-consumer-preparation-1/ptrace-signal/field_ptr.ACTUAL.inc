unsafe fn field_ptr<T>(base: *mut u8, offset: SizeT) -> *mut T {
    base.add(offset).cast::<T>()
}
