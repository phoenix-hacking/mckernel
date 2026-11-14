//! User-mode fixture for the actual no-SIMD Rust object and extracted C oracle.
//! No XSAVE/XRSTOR, kernel execution, or guest acceptance is involved.
use std::alloc::{alloc, dealloc, Layout};
use std::ffi::{c_void, CStr};
use std::ptr::null_mut;

// REAL_THREAD_ABI
use abi::Thread;

extern "C" {
    fn configure_copy(available: i32, size: i32);
    fn reference_copy_fp_regs(from: *const Thread, to: *mut Thread) -> i32;
    fn copy_fp_regs(from: *const Thread, to: *mut Thread) -> i32;
}

static mut ALLOCATION: *mut c_void = null_mut();
static mut ALLOCATIONS: usize = 0;
static mut EXPECTED_PAGES: i32 = 0;
static mut FAIL_ALLOCATION: bool = false;

#[no_mangle]
unsafe extern "C" fn x86_alloc_aligned_pages_node_bridge(
    pages: i32,
    align: i32,
    flags: u64,
    node: i32,
    is_user: i32,
    address: u64,
    file: *mut i8,
    line: i32,
) -> *mut c_void {
    unsafe {
        ALLOCATIONS += 1;
        assert_eq!(pages, { EXPECTED_PAGES });
        assert_eq!(
            (align, flags, node, is_user, address),
            (0, 2, -1, 0, u64::MAX)
        );
        assert_eq!(CStr::from_ptr(file).to_bytes(), b"arch/x86_64/kernel/cpu.c");
        assert!(line > 0);
        if FAIL_ALLOCATION {
            null_mut()
        } else {
            ALLOCATION
        }
    }
}

struct Guarded {
    base: *mut u8,
    layout: Layout,
    length: usize,
}
impl Guarded {
    fn new(length: usize) -> Self {
        let layout = Layout::from_size_align(length + 8192, 4096).unwrap();
        let base = unsafe { alloc(layout) };
        assert!(!base.is_null());
        unsafe { std::ptr::write_bytes(base, 0xa5, layout.size()) };
        Self {
            base,
            layout,
            length,
        }
    }
    fn pointer(&self) -> *mut c_void {
        unsafe { self.base.add(4096).cast() }
    }
    fn bytes(&self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.pointer().cast(), self.length) }
    }
    fn guards(&self) {
        assert!(unsafe { std::slice::from_raw_parts(self.base, 4096) }
            .iter()
            .all(|b| *b == 0xa5));
        assert!(
            unsafe { std::slice::from_raw_parts(self.base.add(4096 + self.length), 4096) }
                .iter()
                .all(|b| *b == 0xa5)
        );
    }
}
impl Drop for Guarded {
    fn drop(&mut self) {
        unsafe { dealloc(self.base, self.layout) }
    }
}

unsafe fn run_case(size: usize, preallocated: bool, absent: bool, fail: bool) {
    let pages = (size + 4095) / 4096;
    let rounded = pages * 4096;
    let source = Guarded::new(size);
    unsafe {
        for i in 0..size {
            *source.pointer().cast::<u8>().add(i) = ((i * 73 + i / 251) & 255) as u8;
        }
    }
    let original_source = source.bytes().to_vec();
    let c_dest = Guarded::new(rounded);
    let rust_dest = Guarded::new(rounded);
    let mut snapshots = Vec::new();
    for (call, destination) in [
        (
            reference_copy_fp_regs as unsafe extern "C" fn(*const Thread, *mut Thread) -> i32,
            &c_dest,
        ),
        (
            copy_fp_regs as unsafe extern "C" fn(*const Thread, *mut Thread) -> i32,
            &rust_dest,
        ),
    ] {
        let mut from: Thread = unsafe { std::mem::zeroed() };
        let mut to: Thread = unsafe { std::mem::zeroed() };
        from.tid = 171;
        to.tid = 172;
        from.fp_regs = if absent { null_mut() } else { source.pointer() };
        to.fp_regs = if preallocated {
            destination.pointer()
        } else {
            null_mut()
        };
        let old_from = from.fp_regs;
        let old_destination = to.fp_regs;
        unsafe {
            configure_copy(1, size as i32);
            ALLOCATION = destination.pointer();
            ALLOCATIONS = 0;
            EXPECTED_PAGES = pages as i32;
            FAIL_ALLOCATION = fail;
        }
        let result = unsafe { call(&from, &mut to) };
        let allocation_expected = !absent && !preallocated;
        assert_eq!(unsafe { ALLOCATIONS }, usize::from(allocation_expected));
        let failed = allocation_expected && fail;
        assert_eq!(result, if failed { -12 } else { 0 });
        assert_eq!(from.fp_regs, old_from);
        assert_eq!((from.tid, to.tid), (171, 172));
        if absent || failed {
            assert_eq!(to.fp_regs, old_destination);
            assert!(destination.bytes().iter().all(|b| *b == 0xa5));
        } else {
            assert_eq!(to.fp_regs, destination.pointer());
            assert_eq!(&destination.bytes()[..size], original_source.as_slice());
            let tail = if preallocated { 0xa5 } else { 0 };
            assert!(destination.bytes()[size..].iter().all(|b| *b == tail));
        }
        destination.guards();
        source.guards();
        assert_eq!(source.bytes(), original_source.as_slice());
        snapshots.push((result, unsafe { ALLOCATIONS }, destination.bytes().to_vec()));
    }
    assert_eq!(snapshots[0], snapshots[1]);
    println!("PASS extent={size} preallocated={preallocated} source_absent={absent} allocation_fail={fail}");
}

fn main() {
    assert_eq!(std::mem::size_of::<Thread>(), 5568);
    assert_eq!(std::mem::align_of::<Thread>(), 64);
    assert_eq!(std::mem::offset_of!(Thread, fp_regs), 4784);
    unsafe {
        for size in [1, 512, 2696, 4096, 4097, 8192, 11008, 12289] {
            for preallocated in [false, true] {
                for absent in [false, true] {
                    for fail in [false, true] {
                        run_case(size, preallocated, absent, fail);
                    }
                }
            }
        }
        // These states violate the C fallback's saved-source precondition;
        // never invoke undefined C memcpy behavior as a negative oracle.
        for (available, size) in [(0, 2696), (1, 0), (1, -1), (0, 0)] {
            let source = Guarded::new(4096);
            let destination = Guarded::new(4096);
            for preallocated in [false, true] {
                let mut from: Thread = std::mem::zeroed();
                let mut to: Thread = std::mem::zeroed();
                from.fp_regs = source.pointer();
                to.fp_regs = if preallocated {
                    destination.pointer()
                } else {
                    null_mut()
                };
                let previous = to.fp_regs;
                ALLOCATIONS = 0;
                configure_copy(available, size);
                assert_eq!(copy_fp_regs(&from, &mut to), -22);
                assert_eq!({ ALLOCATIONS }, 0);
                assert_eq!(to.fp_regs, previous);
                assert!(destination.bytes().iter().all(|b| *b == 0xa5));
                from.fp_regs = null_mut();
                assert_eq!(copy_fp_regs(&from, &mut to), 0);
                assert_eq!(to.fp_regs, previous);
                source.guards();
                destination.guards();
            }
        }
        // Also fail closed on invalid thread pointers without allocating.
        configure_copy(1, 2696);
        ALLOCATIONS = 0;
        let mut to: Thread = std::mem::zeroed();
        assert_eq!(copy_fp_regs(std::ptr::null(), &mut to), -22);
        assert_eq!(copy_fp_regs(&to, std::ptr::null_mut()), -22);
        assert_eq!({ ALLOCATIONS }, 0);
    }
    println!("PASS 64 C/Rust parity cases; 8 invalid configurations; 2 invalid pointers; real Thread ABI");
}
