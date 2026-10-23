#![no_std]
#![allow(dead_code)]
#[path="actual_debug_type.rs"] mod debug;
type CInt=i32;
use core::ptr::read_volatile;
unsafe extern "C" { static mut process_sched_migrate_debug: debug::Ddebug; fn kprintf(format:*const i8,...)->CInt; }
/// Preserve the existing optional migration diagnostic through Rust logging.
/// The C declaration owns only the existing __verbose selector data so current
/// C file/function/line selectors remain stable. Arguments are already evaluated
/// at the caller boundary even when disabled; thread_addr is never dereferenced.
#[no_mangle]
pub unsafe extern "C" fn process_sched_migrate_log_bridge(
    _thread_addr: usize, tid: CInt, cpu_id: CInt,
) {
    let flags = unsafe {
        read_volatile(core::ptr::addr_of!(process_sched_migrate_debug.line_flags)) >> 24
    };
    if flags != 0 {
        unsafe {
            kprintf(
                b"%s: tid: %d -> cpu: %d\n\0".as_ptr().cast(),
                b"sched_request_migrate\0".as_ptr().cast::<i8>(), tid, cpu_id,
            );
        }
    }
}


#[no_mangle]
pub static LEAF_DEBUG_LAYOUT:[usize;6]=[core::mem::size_of::<debug::Ddebug>(),core::mem::align_of::<debug::Ddebug>(),core::mem::offset_of!(debug::Ddebug,file),core::mem::offset_of!(debug::Ddebug,func),core::mem::offset_of!(debug::Ddebug,fmt),core::mem::offset_of!(debug::Ddebug,line_flags)];
#[no_mangle]
pub unsafe extern "C" fn leaf_set_ddebug_flags(dbg: *mut debug::Ddebug, flags: u32) {
    (*dbg).line_flags = ((*dbg).line_flags & 0x00ff_ffff) | (flags << 24);
}
