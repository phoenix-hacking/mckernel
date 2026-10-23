use core::ffi::c_void; type CUInt=u32; type CInt=i32;
type WaitqFunc=Option<unsafe extern "C" fn(*mut WaitqEntry,CUInt,CInt,*mut c_void)->CInt>;
#[repr(C)]
pub(crate) struct IhkSpinlock {
    head_tail: CUInt,
}
#[repr(C)]
pub(crate) struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}
#[repr(C)]
pub(crate) struct WaitqEntry {
    link: ListHead,
    private: *mut c_void,
    flags: CUInt,
    func: WaitqFunc,
}
unsafe extern "C" { fn locked_wake_function(entry:*mut WaitqEntry,mode:CUInt,flags:CInt,key:*mut c_void)->CInt; }
unsafe fn init_list_head(list: *mut ListHead) {
    (*list).next = list;
    (*list).prev = list;
}
unsafe fn entry_link(entry: *mut WaitqEntry) -> *mut ListHead {
    &raw mut (*entry).link
}
#[no_mangle]
pub unsafe extern "C" fn waitq_init_locked_entry(entry: *mut WaitqEntry, proc: *mut c_void) {
    (*entry).private = proc;
    (*entry).flags = 0;
    (*entry).func = Some(locked_wake_function);
    init_list_head(entry_link(entry));
}

#[no_mangle]
pub static LEAF_ENTRY_LAYOUT:[usize;6]=[core::mem::size_of::<WaitqEntry>(),core::mem::align_of::<WaitqEntry>(),
 core::mem::offset_of!(WaitqEntry,link),core::mem::offset_of!(WaitqEntry,private),core::mem::offset_of!(WaitqEntry,flags),core::mem::offset_of!(WaitqEntry,func)];
