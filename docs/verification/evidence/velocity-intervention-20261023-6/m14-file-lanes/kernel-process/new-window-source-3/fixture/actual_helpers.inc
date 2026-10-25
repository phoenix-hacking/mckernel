#[inline(always)]
fn file_ptr() -> *mut c_char {
    PROFILE_FILE.as_ptr() as *mut c_char
}

#[inline(always)]
unsafe fn profile_events(ptr: *mut c_void) -> *mut ProfileEvent {
    ptr.cast::<ProfileEvent>()
}

#[inline(always)]
unsafe fn zero_events(events: *mut ProfileEvent) {
    core::ptr::write_bytes(
        events.cast::<u8>(),
        0,
        size_of::<ProfileEvent>() * PROFILE_EVENT_MAX,
    );
}
