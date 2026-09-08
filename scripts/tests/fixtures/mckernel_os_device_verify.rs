// SPDX-License-Identifier: GPL-2.0-only
//! Borrow ABI checks after the disposable guest starts its first native OS.

use core::{
    ffi::c_void,
    mem::{align_of, offset_of, size_of},
    ptr,
};
use kernel::{bindings, prelude::*, str::CStr};

module! {
    type: DeviceVerify,
    name: "mckernel_os_device_verify",
    author: "McKernel developers",
    description: "Native IHK OS device borrowing verification",
    license: "GPL",
}

// The pinned module! macro has no namespace-import field. Reuse the native
// SMP module's data-only Linux modinfo representation; this fixture is obj-m.
#[used(compiler)]
#[link_section = ".modinfo"]
static IMPORT: [u8; b"import_ns=MCKERNEL_IHK_V1\0".len()] = *b"import_ns=MCKERNEL_IHK_V1\0";

#[used]
#[link_section = ".mckernel_os_device_layout"]
static LAYOUT: [usize; 3] = [
    size_of::<bindings::device>(),
    align_of::<bindings::device>(),
    offset_of!(bindings::device, kobj),
];

type Callback = unsafe extern "C" fn(*mut c_void, *mut c_void) -> i32;

// SAFETY: The actual IHK module owns this exact namespaced borrowing ABI.
extern "C" {
    fn ihk_os_with_kobject_v1(
        slot: u32,
        generation: u64,
        abi: u32,
        context: *mut c_void,
        callback: Option<Callback>,
    ) -> i32;
}

struct Context {
    calls: usize,
    status: i32,
}

// SAFETY: check supplies its unique initialized stack context synchronously;
// IHK lends the actual registered device's Linux kobject for this callback.
unsafe extern "C" fn visit(context: *mut c_void, parent: *mut c_void) -> i32 {
    assert!(!parent.is_null());
    let context = unsafe { &mut *context.cast::<Context>() };
    let object = parent.cast::<bindings::kobject>();
    // SAFETY: The borrowed device registration owns its immutable name.
    let name = unsafe { CStr::from_char_ptr((*object).name) };
    assert_eq!(name.as_bytes(), b"mcos0");
    context.calls += 1;
    context.status
}

fn check(slot: u32, generation: u64, abi: u32, status: i32, expected: i32, calls: usize) {
    let mut context = Context { calls: 0, status };
    // SAFETY: Stack context and callback remain live; no pointer escapes.
    let result = unsafe {
        ihk_os_with_kobject_v1(
            slot,
            generation,
            abi,
            (&mut context as *mut Context).cast(),
            Some(visit),
        )
    };
    assert_eq!(result, expected);
    assert_eq!(context.calls, calls);
}

struct DeviceVerify;

impl kernel::Module for DeviceVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        // The helper loads this only after a fresh IHK lifetime has started
        // mcos0 generation 1. No other create precedes that actual BOOT call.
        // SAFETY: A missing callback must fail before dereferencing context.
        assert_eq!(
            unsafe { ihk_os_with_kobject_v1(0, 1, 1, ptr::null_mut(), None) },
            -22
        );
        for abi in [0, 2, u32::MAX] {
            check(0, 1, abi, 0, -22, 0);
        }
        for slot in [64, u32::MAX] {
            check(slot, 1, 1, 0, -22, 0);
        }
        for generation in [0, 2, u64::MAX] {
            check(0, generation, 1, 0, -116, 0);
        }
        check(1, 1, 1, 0, -2, 0);
        for (status, expected) in [(0, 0), (-12, -12), (-4095, -4095), (1, -5), (-4096, -5)] {
            check(0, 1, 1, status, expected, 1);
        }
        pr_info!(
            "MCKERNEL_OS_DEVICE_VERIFY PASS checks=15 callbacks=5 parent=mcos0 generation=1\n"
        );
        Ok(Self)
    }
}
