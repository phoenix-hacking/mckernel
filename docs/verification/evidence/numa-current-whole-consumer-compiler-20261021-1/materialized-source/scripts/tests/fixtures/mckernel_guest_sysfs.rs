// SPDX-License-Identifier: GPL-2.0-only
//! Opt-in verification in a real McKernel image, using its public sysfs API.
//! Metadata waits run on the boot thread with interrupts enabled. IRQ callbacks
//! only access retained static values and atomics; none waits for host metadata.

use crate::abi::{CInt, SysfsBitmapParam, SysfsHandle, SysfsOps};
use crate::sysfs::{sysfs_createf, sysfs_lookupf, sysfs_mkdirf, sysfs_symlinkf, sysfs_unlinkf};
use core::ffi::{c_char, c_void, CStr};
use core::ptr::null_mut;
use core::sync::atomic::{AtomicU32, AtomicU64, Ordering};

unsafe extern "C" {
    fn kprintf(format: *const c_char, ...) -> CInt;
    fn snprintf(buffer: *mut c_char, size: usize, format: *const c_char, ...) -> CInt;
    fn cpu_pause();
    #[link_name = "panic"]
    fn kernel_panic(message: *const c_char) -> !;
}

macro_rules! ensure {
    ($value:expr) => {
        if !$value {
            unsafe {
                kprintf(
                    c"NATIVE_GUEST_SYSFS FAIL line=%d\n".as_ptr(),
                    line!() as CInt,
                );
                kernel_panic(c"native guest sysfs verification".as_ptr());
            }
        }
    };
}

const KEEP_ANCESTOR: CInt = 1;
const READONLY: usize = 4;
const ERROR: usize = 5;
const BOUNDARY: usize = 6;
const BAD_COUNT: usize = 7;
const DUPLICATE: usize = 8;
static PHASE: AtomicU32 = AtomicU32::new(0);
static METADATA: AtomicU32 = AtomicU32::new(0);
static FULL_MASK: [u64; 228] = [u64::MAX; 228];

struct Entry {
    kind: usize,
    value: AtomicU64,
    shows: AtomicU32,
    stores: AtomicU32,
    releases: AtomicU32,
}

impl Entry {
    const fn new(kind: usize) -> Self {
        Self {
            kind,
            value: AtomicU64::new(0),
            shows: AtomicU32::new(0),
            stores: AtomicU32::new(0),
            releases: AtomicU32::new(0),
        }
    }
}

static ENTRIES: [Entry; 9] = [
    Entry::new(0),
    Entry::new(1),
    Entry::new(2),
    Entry::new(3),
    Entry::new(READONLY),
    Entry::new(ERROR),
    Entry::new(BOUNDARY),
    Entry::new(BAD_COUNT),
    Entry::new(DUPLICATE),
];

static OPS: SysfsOps = SysfsOps {
    show: Some(show),
    store: Some(store),
    release: Some(release),
};
static READONLY_OPS: SysfsOps = SysfsOps {
    show: Some(show),
    store: None,
    release: Some(release),
};
static STATUS_OPS: SysfsOps = SysfsOps {
    show: Some(status),
    store: None,
    release: None,
};
static CONTROL_OPS: SysfsOps = SysfsOps {
    show: None,
    store: Some(control),
    release: None,
};

fn instance(index: usize) -> *mut c_void {
    (&ENTRIES[index] as *const Entry).cast_mut().cast()
}

fn entry(pointer: *mut c_void) -> &'static Entry {
    // Compare tokens before creating any reference from a received instance.
    for index in 0..ENTRIES.len() {
        if pointer == instance(index) {
            return &ENTRIES[index];
        }
    }
    ensure!(false);
    unreachable!()
}

fn count_result(count: CInt, capacity: usize) -> isize {
    if count < 0 || count as usize >= capacity {
        -75
    } else {
        count as isize
    }
}

unsafe extern "C" fn show(
    _ops: *mut SysfsOps,
    pointer: *mut c_void,
    buffer: *mut c_void,
    capacity: usize,
) -> isize {
    let value = entry(pointer);
    ensure!(value.releases.load(Ordering::Acquire) == 0);
    value.shows.fetch_add(1, Ordering::Relaxed);
    match value.kind {
        0..=3 => count_result(
            unsafe {
                snprintf(
                    buffer.cast(),
                    capacity,
                    c"%llu\n".as_ptr(),
                    value.value.load(Ordering::Acquire),
                )
            },
            capacity,
        ),
        READONLY => count_result(
            unsafe { snprintf(buffer.cast(), capacity, c"readonly\n".as_ptr()) },
            capacity,
        ),
        ERROR => -22,
        BOUNDARY => {
            ensure!(capacity == 4096);
            unsafe { core::ptr::write_bytes(buffer.cast::<u8>(), b'z', 4095) };
            4095
        }
        BAD_COUNT => (capacity + 1) as isize,
        _ => {
            ensure!(false);
            -22
        }
    }
}

unsafe extern "C" fn store(
    _ops: *mut SysfsOps,
    pointer: *mut c_void,
    buffer: *mut c_void,
    size: usize,
) -> isize {
    let value = entry(pointer);
    ensure!(value.releases.load(Ordering::Acquire) == 0);
    value.stores.fetch_add(1, Ordering::Relaxed);
    if size > 4096 {
        return -22;
    }
    let bytes = unsafe { core::slice::from_raw_parts(buffer.cast::<u8>(), size) };
    match value.kind {
        0..=3 => {
            if bytes.len() < 2 || bytes.len() > 20 || bytes.last() != Some(&b'\n') {
                return -22;
            }
            let mut number = 0u64;
            for &byte in &bytes[..bytes.len() - 1] {
                if !byte.is_ascii_digit() {
                    return -22;
                }
                number = match number
                    .checked_mul(10)
                    .and_then(|n| n.checked_add((byte - b'0') as u64))
                {
                    Some(n) => n,
                    None => return -22,
                };
            }
            value.value.store(number, Ordering::Release);
            size as isize
        }
        ERROR => -22,
        BOUNDARY => {
            ensure!(bytes.len() == 4096 && bytes.iter().all(|&byte| byte == b'k'));
            size as isize
        }
        BAD_COUNT => (size + 1) as isize,
        _ => {
            ensure!(false);
            -22
        }
    }
}

unsafe extern "C" fn release(_ops: *mut SysfsOps, pointer: *mut c_void) {
    let value = entry(pointer);
    ensure!(value.kind != DUPLICATE);
    ensure!(value.releases.fetch_add(1, Ordering::AcqRel) == 0);
}

fn totals() -> (u32, u32, u32) {
    let releases = ENTRIES[..DUPLICATE]
        .iter()
        .map(|v| v.releases.load(Ordering::Acquire))
        .sum();
    let shows = ENTRIES[..4]
        .iter()
        .map(|v| v.shows.load(Ordering::Acquire))
        .sum();
    let stores = ENTRIES[..4]
        .iter()
        .map(|v| v.stores.load(Ordering::Acquire))
        .sum();
    (releases, shows, stores)
}

unsafe extern "C" fn status(
    _ops: *mut SysfsOps,
    _pointer: *mut c_void,
    buffer: *mut c_void,
    capacity: usize,
) -> isize {
    let phase = PHASE.load(Ordering::Acquire);
    let (releases, shows, stores) = totals();
    count_result(
        unsafe {
            snprintf(
                buffer.cast(),
                capacity,
                c"%u %u %u %u %u\n".as_ptr(),
                phase,
                releases,
                ENTRIES[DUPLICATE].releases.load(Ordering::Acquire),
                shows,
                stores,
            )
        },
        capacity,
    )
}

unsafe extern "C" fn control(
    _ops: *mut SysfsOps,
    _pointer: *mut c_void,
    buffer: *mut c_void,
    size: usize,
) -> isize {
    if size > 8 {
        return -22;
    }
    let bytes = unsafe { core::slice::from_raw_parts(buffer.cast::<u8>(), size) };
    let (before, after) = match bytes {
        b"advance\n" => (0, 1),
        b"finish\n" => (2, 3),
        _ => return -22,
    };
    // Returning from the interrupt completes the reply before the boot thread
    // resumes and issues any blocking UNLINK request.
    if PHASE
        .compare_exchange(before, after, Ordering::AcqRel, Ordering::Acquire)
        .is_err()
    {
        -16
    } else {
        size as isize
    }
}

unsafe fn expected(actual: CInt, wanted: CInt) {
    METADATA.fetch_add(1, Ordering::Relaxed);
    if actual != wanted {
        unsafe {
            kprintf(
                c"NATIVE_GUEST_SYSFS metadata actual=%d expected=%d\n".as_ptr(),
                actual,
                wanted,
            )
        };
    }
    ensure!(actual == wanted);
}

unsafe fn publish(path: &CStr, index: usize) {
    let ops = if index == READONLY {
        &READONLY_OPS
    } else {
        &OPS
    };
    unsafe {
        expected(
            sysfs_createf(
                (ops as *const SysfsOps).cast_mut(),
                instance(index),
                0o644,
                path.as_ptr(),
            ),
            0,
        )
    };
}

unsafe fn wait_phase(wanted: u32) {
    while PHASE.load(Ordering::Acquire) != wanted {
        unsafe { cpu_pause() };
    }
}

pub(crate) unsafe fn run() {
    unsafe {
        let mut directory = SysfsHandle { handle: 0 };
        let mut found = SysfsHandle { handle: 0 };
        expected(
            sysfs_mkdirf(&mut directory, c"/sys/test/native".as_ptr()),
            0,
        );
        expected(sysfs_lookupf(&mut found, c"/sys/test/native".as_ptr()), 0);
        ensure!(directory.handle != 0 && found.handle == directory.handle);
        expected(sysfs_mkdirf(null_mut(), c"/sys/test/native".as_ptr()), -17);
        expected(sysfs_unlinkf(0, c"/sys".as_ptr()), -1);
        expected(
            sysfs_mkdirf(&mut directory, c"/sys/test/native/target".as_ptr()),
            0,
        );
        expected(
            sysfs_lookupf(&mut found, c"/sys/test/native/target".as_ptr()),
            0,
        );
        ensure!(directory.handle != 0 && found.handle == directory.handle);
        expected(
            sysfs_symlinkf(
                SysfsHandle {
                    handle: directory.handle,
                },
                c"/sys/test/native/link".as_ptr(),
            ),
            0,
        );
        expected(
            sysfs_symlinkf(
                SysfsHandle {
                    handle: directory.handle,
                },
                c"/sys/test/native/link".as_ptr(),
            ),
            -17,
        );
        expected(
            sysfs_mkdirf(&mut directory, c"/sys/test/native/temporary/leaf".as_ptr()),
            0,
        );
        expected(
            sysfs_unlinkf(0, c"/sys/test/native/temporary/leaf".as_ptr()),
            0,
        );
        expected(
            sysfs_lookupf(&mut found, c"/sys/test/native/temporary/leaf".as_ptr()),
            -2,
        );
        expected(
            sysfs_lookupf(&mut found, c"/sys/test/native/temporary".as_ptr()),
            -2,
        );
        expected(
            sysfs_symlinkf(directory, c"/sys/test/native/stale-prefix/link".as_ptr()),
            -2,
        );
        expected(
            sysfs_lookupf(&mut found, c"/sys/test/native/stale-prefix".as_ptr()),
            -2,
        );
        for index in 0..4 {
            expected(
                sysfs_createf(
                    (&OPS as *const SysfsOps).cast_mut(),
                    instance(index),
                    0o644,
                    c"/sys/test/native/items/value%u".as_ptr(),
                    index as u32,
                ),
                0,
            );
        }
        expected(
            sysfs_createf(
                (&OPS as *const SysfsOps).cast_mut(),
                instance(DUPLICATE),
                0o644,
                c"/sys/test/native/items/value0".as_ptr(),
            ),
            -17,
        );
        publish(c"/sys/test/native/items/readonly", READONLY);
        publish(c"/sys/test/native/items/error", ERROR);
        publish(c"/sys/test/native/items/boundary", BOUNDARY);
        publish(c"/sys/test/native/items/bad-count", BAD_COUNT);
        let mut bitmap = SysfsBitmapParam {
            nbits: 14560,
            padding: 0,
            ptr: FULL_MASK.as_ptr().cast_mut().cast(),
        };
        expected(
            sysfs_createf(
                7usize as *mut SysfsOps,
                (&mut bitmap as *mut SysfsBitmapParam).cast(),
                0o644,
                c"/sys/test/native/items/full-mask".as_ptr(),
            ),
            0,
        );
        expected(
            sysfs_createf(
                (&STATUS_OPS as *const SysfsOps).cast_mut(),
                null_mut(),
                0o444,
                c"/sys/test/native/status".as_ptr(),
            ),
            0,
        );
        // Publish control last, so its existence admits the Linux reader.
        expected(
            sysfs_createf(
                (&CONTROL_OPS as *const SysfsOps).cast_mut(),
                null_mut(),
                0o222,
                c"/sys/test/native/control".as_ptr(),
            ),
            0,
        );
        kprintf(c"NATIVE_GUEST_SYSFS published\n".as_ptr());
        wait_phase(1);
        for (index, value) in ENTRIES[..4].iter().enumerate() {
            ensure!(value.shows.load(Ordering::Acquire) == 65);
            ensure!(value.stores.load(Ordering::Acquire) == 64);
            ensure!(value.value.load(Ordering::Acquire) == (index as u64 + 1) * 1_000_000 + 63);
        }
        for (index, value) in ENTRIES[READONLY..DUPLICATE].iter().enumerate() {
            ensure!(value.shows.load(Ordering::Acquire) == 1);
            ensure!(value.stores.load(Ordering::Acquire) == u32::from(index != 0));
        }
        ensure!(totals().0 == 0);
        expected(
            sysfs_unlinkf(KEEP_ANCESTOR, c"/sys/test/native/items".as_ptr()),
            0,
        );
        expected(
            sysfs_lookupf(&mut found, c"/sys/test/native/items".as_ptr()),
            -2,
        );
        for value in &ENTRIES[..DUPLICATE] {
            ensure!(value.releases.load(Ordering::Acquire) == 1);
        }
        ensure!(ENTRIES[DUPLICATE].releases.load(Ordering::Acquire) == 0);
        PHASE.store(2, Ordering::Release);
        wait_phase(3);
        expected(
            sysfs_unlinkf(KEEP_ANCESTOR, c"/sys/test/native".as_ptr()),
            0,
        );
        for name in [c"d32", c"d64", c"u32", c"u64", c"s", c"pbl", c"pb", c"u32K"] {
            expected(
                sysfs_unlinkf(
                    KEEP_ANCESTOR,
                    c"/sys/test/remote/%s".as_ptr(),
                    name.as_ptr(),
                ),
                0,
            );
        }
        let (releases, shows, stores) = totals();
        kprintf(c"NATIVE_GUEST_SYSFS PASS metadata=%u releases=%u forbidden=0 value_reads=%u value_stores=%u\n".as_ptr(),
            METADATA.load(Ordering::Acquire), releases, shows, stores);
    }
}
