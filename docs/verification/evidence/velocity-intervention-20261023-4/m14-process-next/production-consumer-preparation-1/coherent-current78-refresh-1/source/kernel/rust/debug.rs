use core::ffi::{c_void, VaList};
use core::ptr::{null_mut, read_volatile, write_volatile};

use crate::abi::{CInt, CLong, CULong, IhkSpinlock, SSizeT, SizeT, SysfsOps};

const EINVAL: CInt = 22;
const INT_MAX: CLong = 2_147_483_647;
const DDEBUG_NONE: u32 = 0;
const DDEBUG_PRINT: u32 = 1;
const IHK_OS_EVENTFD_TYPE_KMSG: CInt = 101;
const IHK_KMSG_SIZE: CInt = (4 << 20) - 4096;
const IHK_KMSG_HIGH_WATER_MARK: CInt = IHK_KMSG_SIZE / 2;
const IHK_KMSG_NOTIFY_DELAY: CInt = 400;
const KPRINTF_LOCAL_BUF_LEN: SizeT = 1024;

#[repr(C)]
pub struct IhkKmsgBuf {
    pub lock: CInt,
    pub tail: CInt,
    pub len: CInt,
    pub head: CInt,
    pub padding: [i8; 4096 - core::mem::size_of::<CInt>() * 4],
    pub str_: [i8; IHK_KMSG_SIZE as usize],
}

#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<IhkKmsgBuf>() == 4 << 20);
    assert!(offset_of!(IhkKmsgBuf, str_) == 4096);
    assert!(size_of::<Ddebug>() == 32);
    assert!(align_of::<Ddebug>() == 8);
    assert!(offset_of!(Ddebug, line_flags) == 24);
};

#[no_mangle]
pub static mut kmsg_buf: *mut IhkKmsgBuf = null_mut();

static mut KMSG_LOCK: IhkSpinlock = IhkSpinlock { head_tail: 0 };
static mut DYNAMIC_DEBUG_SYSFS_OPS: SysfsOps = SysfsOps {
    show: Some(dynamic_debug_sysfs_show),
    store: Some(dynamic_debug_sysfs_store),
    release: None,
};

unsafe extern "C" {
    static mut __start___verbose: Ddebug;
    static mut __stop___verbose: Ddebug;

    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
    fn cpu_disable_interrupt_save() -> CULong;
    fn cpu_restore_interrupt(flags: CULong);
    fn cpu_pause();
    fn cpu_interrupt_disabled() -> CInt;
    fn ihk_mc_delay_us(us: CInt);
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_mc_spinlock_init(lock: *mut IhkSpinlock);
    fn eventfd(type_: CInt);
    fn sysfs_createf(
        ops: *mut SysfsOps,
        instance: *mut c_void,
        mode: CInt,
        fmt: *const i8,
        ...
    ) -> CInt;
}

#[inline(always)]
fn ddebug_line(dbg: *const Ddebug) -> CInt {
    unsafe { ((*dbg).line_flags & 0x00ff_ffff) as CInt }
}

#[inline(always)]
unsafe fn ddebug_flags(dbg: *const Ddebug) -> u32 {
    (*dbg).line_flags >> 24
}

#[inline(always)]
unsafe fn set_ddebug_flags(dbg: *mut Ddebug, flags: u32) {
    (*dbg).line_flags = ((*dbg).line_flags & 0x00ff_ffff) | (flags << 24);
}

#[inline(always)]
unsafe fn kmsg() -> *mut IhkKmsgBuf {
    read_volatile(&raw const kmsg_buf)
}

#[inline(always)]
unsafe fn kmsg_used(buf: *const IhkKmsgBuf) -> CInt {
    let tail = (*buf).tail as u32;
    let head = (*buf).head as u32;
    let len = (*buf).len as u32;

    if len == 0 {
        0
    } else if tail >= head {
        tail.wrapping_sub(head) as CInt
    } else {
        tail.wrapping_add(len).wrapping_sub(head) as CInt
    }
}

#[inline(always)]
unsafe fn kmsg_margin(buf: *const IhkKmsgBuf) -> CInt {
    let tail = (*buf).tail as u32;
    let head = (*buf).head as u32;
    let len = (*buf).len as u32;

    if len == 0 {
        0
    } else if head == tail {
        len as CInt
    } else if head > tail {
        head.wrapping_sub(tail) as CInt
    } else {
        head.wrapping_add(len).wrapping_sub(tail) as CInt
    }
}

#[inline(always)]
unsafe fn debug_spin_lock_irqsave(lock: *mut CInt) -> CULong {
    let flags = cpu_disable_interrupt_save();
    while core::sync::atomic::AtomicI32::from_ptr(lock)
        .compare_exchange(
            0,
            1,
            core::sync::atomic::Ordering::SeqCst,
            core::sync::atomic::Ordering::SeqCst,
        )
        .is_err()
    {
        cpu_pause();
    }
    flags
}

#[inline(always)]
unsafe fn debug_spin_unlock_irqrestore(lock: *mut CInt, flags: CULong) {
    write_volatile(lock, 0);
    cpu_restore_interrupt(flags);
}

unsafe fn memcpy_ringbuf(src: *const i8, len: CInt) {
    let buf = kmsg();
    if buf.is_null() || (*buf).len <= 0 {
        return;
    }

    let mut i = 0;
    while i < len {
        *(*buf).str_.as_mut_ptr().add((*buf).tail as usize) = *src.add(i as usize);
        let next = (*buf).tail + 1;
        (*buf).tail = if next >= (*buf).len { 0 } else { next };
        i += 1;
    }
}

unsafe fn notify_kmsg_if_needed(buf: *const IhkKmsgBuf) {
    if cpu_interrupt_disabled() == 0 && kmsg_used(buf) > IHK_KMSG_HIGH_WATER_MARK {
        eventfd(IHK_OS_EVENTFD_TYPE_KMSG);
        ihk_mc_delay_us(IHK_KMSG_NOTIFY_DELAY);
    }
}

#[no_mangle]
pub unsafe extern "C" fn kprintf_lock() -> CULong {
    __ihk_mc_spinlock_lock(&raw mut KMSG_LOCK)
}

#[no_mangle]
pub unsafe extern "C" fn kprintf_unlock(irqflags: CULong) {
    __ihk_mc_spinlock_unlock(&raw mut KMSG_LOCK, irqflags);
}

#[no_mangle]
pub unsafe extern "C" fn kputs(buf: *mut i8) {
    let msg = kmsg();
    if msg.is_null() || buf.is_null() {
        return;
    }

    let len = crate::string::strlen(buf.cast_const()) as CInt;
    let flags_outer = kprintf_lock();
    let flags_inner = debug_spin_lock_irqsave(&raw mut (*msg).lock);
    let overflow = kmsg_margin(msg) <= len;

    memcpy_ringbuf(buf.cast_const(), len);
    if overflow {
        let next = (*msg).tail + 1;
        (*msg).head = if next >= (*msg).len { 0 } else { next };
    }

    debug_spin_unlock_irqrestore(&raw mut (*msg).lock, flags_inner);
    kprintf_unlock(flags_outer);
    notify_kmsg_if_needed(msg);
}

unsafe fn vkprintf_locked(format: *const i8, args: &mut VaList<'_>, take_outer_lock: bool) -> CInt {
    let msg = kmsg();
    if msg.is_null() {
        return -EINVAL;
    }

    let mut local = [0i8; KPRINTF_LOCAL_BUF_LEN];
    let mut len = crate::numparse::snprintf(
        local.as_mut_ptr(),
        KPRINTF_LOCAL_BUF_LEN,
        c"[%3d]: ".as_ptr().cast(),
        ihk_mc_get_processor_id(),
    );
    len += crate::numparse::vsnprintf_va_list_result(
        local.as_mut_ptr().add(len as usize),
        KPRINTF_LOCAL_BUF_LEN - len as SizeT - 2,
        format,
        args,
    );

    let flags_outer = if take_outer_lock { kprintf_lock() } else { 0 };
    let flags_inner = debug_spin_lock_irqsave(&raw mut (*msg).lock);
    let overflow = kmsg_margin(msg) <= len;

    memcpy_ringbuf(local.as_ptr(), len);
    if overflow {
        let next = (*msg).tail + 1;
        (*msg).head = if next >= (*msg).len { 0 } else { next };
    }

    debug_spin_unlock_irqrestore(&raw mut (*msg).lock, flags_inner);
    if take_outer_lock {
        kprintf_unlock(flags_outer);
    }
    notify_kmsg_if_needed(msg);

    len
}

#[no_mangle]
pub unsafe extern "C" fn __kprintf(format: *const i8, mut args: ...) -> CInt {
    vkprintf_locked(format, &mut args, false)
}

#[no_mangle]
pub unsafe extern "C" fn kprintf(format: *const i8, mut args: ...) -> CInt {
    vkprintf_locked(format, &mut args, true)
}

#[no_mangle]
pub unsafe extern "C" fn kmsg_init() {
    ihk_mc_spinlock_init(&raw mut KMSG_LOCK);
}

unsafe extern "C" fn dynamic_debug_sysfs_show(
    _ops: *mut SysfsOps,
    _instance: *mut c_void,
    buf: *mut c_void,
    size: SizeT,
) -> SSizeT {
    let out = buf.cast::<i8>();
    let mut n = crate::numparse::snprintf(
        out,
        size,
        c"# filename:lineno function flags format\n".as_ptr().cast(),
    ) as SSizeT;
    let mut dbg = &raw mut __start___verbose;
    let end = &raw mut __stop___verbose;

    while dbg < end {
        n += crate::numparse::snprintf(
            out.add(n as usize),
            size.wrapping_sub(n as SizeT),
            c"%s:%d %s =%s\n".as_ptr().cast(),
            (*dbg).file,
            ddebug_line(dbg),
            (*dbg).func,
            if ddebug_flags(dbg) != 0 {
                c"p".as_ptr()
            } else {
                c"_".as_ptr()
            },
        ) as SSizeT;
        if n as SizeT >= size {
            break;
        }
        dbg = dbg.add(1);
    }

    n
}

#[inline(always)]
unsafe fn skip_to_token_end(mut cur: *mut i8) -> *mut i8 {
    let next = crate::string::strpbrk(cur, c" \n".as_ptr().cast());
    if !next.is_null() {
        cur = next;
        *cur = 0;
        cur = cur.add(1);
    } else {
        cur = null_mut();
    }
    cur
}

#[inline(always)]
unsafe fn flag_pair(ch0: i8, ch1: i8) -> CInt {
    ch0 as CInt + 256 * ch1 as CInt
}

unsafe extern "C" fn dynamic_debug_sysfs_store(
    _ops: *mut SysfsOps,
    _instance: *mut c_void,
    buf: *mut c_void,
    size: SizeT,
) -> SSizeT {
    if buf.is_null() || size == 0 {
        return -EINVAL as SSizeT;
    }

    let head = buf.cast::<i8>();
    let mut cur = head;
    let end = head.add(size);
    let mut file: *mut i8 = null_mut();
    let mut func: *mut i8 = null_mut();
    let mut line_start: CLong = 0;
    let mut line_end: CLong = INT_MAX;
    let mut set_flag: CInt = -1;

    *head.add(size - 1) = 0;

    loop {
        while !cur.is_null() && cur < end && *cur != 0 {
            if crate::string::strncmp(cur, c"func ".as_ptr().cast(), 5) == 0 {
                cur = cur.add(5);
                func = cur;
            } else if crate::string::strncmp(cur, c"file ".as_ptr().cast(), 5) == 0 {
                cur = cur.add(5);
                file = cur;
            } else if crate::string::strncmp(cur, c"line ".as_ptr().cast(), 5) == 0 {
                let mut next: *mut i8 = null_mut();
                cur = cur.add(5);
                if *cur != b'-' as i8 {
                    line_start =
                        crate::numparse::strtol(cur.cast_const(), &raw mut next, 0) as CLong;
                    cur = next;
                }
                if *cur != b'-' as i8 {
                    line_end = line_start;
                } else {
                    cur = cur.add(1);
                    if *cur == b' ' as i8 || *cur == 0 {
                        line_end = INT_MAX;
                    } else {
                        line_end =
                            crate::numparse::strtol(cur.cast_const(), &raw mut next, 0) as CLong;
                        cur = next;
                    }
                }
            } else if !crate::string::strchr(c"+-=".as_ptr().cast(), *cur as CInt).is_null() {
                match flag_pair(*cur, *cur.add(1)) {
                    x if x == flag_pair(b'+' as i8, b'p' as i8)
                        || x == flag_pair(b'=' as i8, b'p' as i8) =>
                    {
                        set_flag = DDEBUG_PRINT as CInt;
                    }
                    x if x == flag_pair(b'-' as i8, b'p' as i8)
                        || x == flag_pair(b'=' as i8, b'_' as i8) =>
                    {
                        set_flag = DDEBUG_NONE as CInt;
                    }
                    _ => {
                        kprintf(
                            c"invalid flag: %.*s\n".as_ptr().cast(),
                            end.offset_from(cur) as CInt,
                            cur,
                        );
                        return -EINVAL as SSizeT;
                    }
                }
                cur = cur.add(3);
                break;
            } else {
                kprintf(
                    c"dynamic debug control: unrecognized keyword: %.*s\n"
                        .as_ptr()
                        .cast(),
                    end.offset_from(cur) as CInt,
                    cur,
                );
                return -EINVAL as SSizeT;
            }
            cur = skip_to_token_end(cur);
        }

        if set_flag < 0 {
            kprintf(c"dynamic debug control: no flag set?\n".as_ptr().cast());
            return -EINVAL as SSizeT;
        }
        if func.is_null() && file.is_null() {
            kprintf(c"at least file or func should be set\n".as_ptr().cast());
            return -EINVAL as SSizeT;
        }

        let mut dbg = &raw mut __start___verbose;
        let stop = &raw mut __stop___verbose;
        while dbg < stop {
            if (func.is_null() || crate::string::strcmp(func, (*dbg).func) == 0)
                && (file.is_null() || crate::string::strcmp(file, (*dbg).file) == 0)
                && ddebug_line(dbg) as CLong >= line_start
                && ddebug_line(dbg) as CLong <= line_end
            {
                set_ddebug_flags(dbg, set_flag as u32);
            }
            dbg = dbg.add(1);
        }

        if cur.is_null() || cur >= end || *cur == 0 {
            break;
        }
    }

    size as SSizeT
}

#[no_mangle]
pub unsafe extern "C" fn dynamic_debug_sysfs_setup() {
    let error = sysfs_createf(
        &raw mut DYNAMIC_DEBUG_SYSFS_OPS,
        null_mut(),
        0o644,
        c"/sys/kernel/debug/dynamic_debug/control".as_ptr().cast(),
    );
    if error != 0 {
        kprintf(
            c"%s: ERROR: creating dynamic_debug/control sysfs file"
                .as_ptr()
                .cast(),
            c"dynamic_debug_sysfs_setup".as_ptr(),
        );
    }
}
