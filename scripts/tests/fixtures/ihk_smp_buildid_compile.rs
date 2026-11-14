// Source-only fixture. The Python harness inserts the production constants,
// dispatcher and callbacks below. UserSlice is a mock: these tests prove Rust
// dispatch, bounds and error propagation, not Linux usercopy or runtime behavior.

type Result<T> = core::result::Result<T, i32>;
const EINVAL: i32 = -22;
const EFAULT: i32 = -14;

#[derive(Default)]
struct CopyState {
    address: usize,
    slice_length: usize,
    constructions: usize,
    writes: usize,
    copied: Vec<u8>,
    fault_after: Option<usize>,
}

std::thread_local! {
    static COPY: std::cell::RefCell<CopyState> = Default::default();
    static CPU_CALL: std::cell::RefCell<Option<(u32, usize, bool)>> = const { std::cell::RefCell::new(None) };
    static MEMORY_CALL: std::cell::RefCell<Option<(u32, usize, bool)>> = const { std::cell::RefCell::new(None) };
}

// The CPU adapter is a separate real Kbuild/guest boundary. This fixture
// records routing only and deliberately performs no Linux hotplug effects.
mod cpu_abi {
    // PRODUCTION_CPU_ABI_CONSTANTS
}
mod smp_cpu {
    use crate::cpu_abi as abi;
    // PRODUCTION_CPU_HANDLES
    pub fn ioctl(command: u32, argument: usize, compat: bool) -> crate::Result<isize> {
        crate::CPU_CALL.with(|call| *call.borrow_mut() = Some((command, argument, compat)));
        Err(-16)
    }
}

// Real allocation and ownership are covered by the separate native guest.
// This boundary checks the production memory routing and pointer conversion.
mod memory_abi {
    // PRODUCTION_MEMORY_ABI_CONSTANTS
}
mod smp_memory {
    use crate::memory_abi as abi;
    // PRODUCTION_MEMORY_HANDLES
    pub fn ioctl(command: u32, argument: usize, compat: bool) -> crate::Result<isize> {
        crate::MEMORY_CALL.with(|call| *call.borrow_mut() = Some((command, argument, compat)));
        Err(-12)
    }
}

mod kernel {
    pub mod bindings { pub struct module; }
    pub mod uaccess {
        pub struct UserSlice;
        pub struct UserSliceWriter;

        impl UserSlice {
            pub fn new(address: usize, length: usize) -> Self {
                crate::COPY.with(|state| {
                    let mut state = state.borrow_mut();
                    state.address = address;
                    state.slice_length = length;
                    state.constructions += 1;
                });
                Self
            }

            pub fn writer(self) -> UserSliceWriter {
                UserSliceWriter
            }
        }

        impl UserSliceWriter {
            pub fn write_slice(&mut self, bytes: &[u8]) -> crate::Result<()> {
                crate::COPY.with(|state| {
                    let mut state = state.borrow_mut();
                    state.writes += 1;
                    assert_eq!(bytes.len(), state.slice_length);
                    if let Some(count) = state.fault_after {
                        state
                            .copied
                            .extend_from_slice(&bytes[..count.min(bytes.len())]);
                        return Err(crate::EFAULT);
                    }
                    state.copied.extend_from_slice(bytes);
                    Ok(())
                })
            }
        }
    }
}

// PRODUCTION_BUILDID_CONSTANTS
// PRODUCTION_BUILDID_DISPATCH
// PRODUCTION_DEVICE_REQUEST

struct ThisModule;
static THIS_MODULE: ThisModule = ThisModule;
impl ThisModule { fn as_ptr(&self) -> *mut kernel::bindings::module { core::ptr::null_mut() } }
fn provider_status_error(value: i64) -> i32 { value as i32 }
// The device-request branch is present in the extracted production callback.
// OS ownership is exercised by the separate complete-adapter fixture.
unsafe extern "C" fn ihk_smp_os_ioctl_v2(_slot: u32, _generation: u64, _command: u32,
    _argument: u64, _compat: u32) -> i64 { -22 }
unsafe extern "C" fn ihk_smp_os_release_v2(_slot: u32, _generation: u64) -> i32 { 0 }
unsafe fn ihk_os_create_unbooted_v2(_minor: u32, _owner: *mut kernel::bindings::module,
    _argument: u64, version: u32,
    ioctl: Option<unsafe extern "C" fn(u32, u64, u32, u64, u32) -> i64>,
    release: Option<unsafe extern "C" fn(u32, u64) -> i32>) -> i64
{
    assert_eq!(version, 1);
    assert!(ioctl.is_some() && release.is_some());
    -12
}
unsafe extern "C" fn ihk_smp_shutdown_v6(_slot: u32, _generation: u64) -> i64 { -38 }
unsafe fn ihk_os_create_unbooted_v6(
    _minor: u32,
    _owner: *mut core::ffi::c_void,
    _argument: u64,
    callback_abi: u32,
    ioctl: Option<unsafe extern "C" fn(u32, u64, u32, u64, u32) -> i64>,
    release: Option<unsafe extern "C" fn(u32, u64) -> i32>,
    prepare: Option<unsafe extern "C" fn(u32, u64, u64, u64) -> i32>,
    start: Option<unsafe extern "C" fn(u32, u64) -> i32>,
    open: Option<application_abi::Open>,
    invoke: Option<application_abi::Invoke>,
    close: Option<application_abi::Close>,
    shutdown: Option<unsafe extern "C" fn(u32, u64) -> i64>,
) -> i64 {
    assert_eq!(callback_abi, 1);
    assert!(ioctl.is_some() && release.is_some() && prepare.is_some() && start.is_some());
    assert!(open.is_some() && invoke.is_some() && close.is_some());
    assert!(shutdown.is_some());
    -12
}
unsafe fn ihk_os_destroy_unbooted_v1(_provider: u32, _minor: u64) -> i64 { -22 }

struct ProviderOpenLease;
struct IhkSmpControlDevice;

// These are the exact callback shapes consumed by the extracted production
// CREATE_OS branch.  The fixture does not model an OS or application; it only
// proves that production dispatch supplies the complete v6 callback bundle.
mod application_abi {
    pub type Open = unsafe extern "C" fn(
        u32,
        u64,
        i32,
        *mut *mut core::ffi::c_void,
    ) -> i32;
    pub type Invoke = unsafe extern "C" fn(
        *mut core::ffi::c_void,
        u32,
        *mut u8,
        usize,
    ) -> i64;
    pub type Close = unsafe extern "C" fn(*mut core::ffi::c_void);
}

fn compatibility_build_id(argument: usize) -> Result<isize> {
    kernel::uaccess::UserSlice::new(argument, IHK_COMPAT_BUILD_ID.len())
        .writer()
        .write_slice(IHK_COMPAT_BUILD_ID)?;
    Ok(0)
}

unsafe extern "C" fn ihk_smp_prepare_boot_v3(
    _slot: u32,
    _generation: u64,
    _kmsg: u64,
    _kmsg_bytes: u64,
) -> i32 {
    -11
}

unsafe extern "C" fn ihk_smp_start_boot_v3(_slot: u32, _generation: u64) -> i32 {
    -11
}

unsafe extern "C" fn application_open(
    _slot: u32,
    _generation: u64,
    _pid: i32,
    output: *mut *mut core::ffi::c_void,
) -> i32 {
    // The mock never publishes an application context.
    unsafe { output.write(core::ptr::null_mut()) };
    -12
}

unsafe extern "C" fn application_invoke(
    _context: *mut core::ffi::c_void,
    _command: u32,
    _buffer: *mut u8,
    _bytes: usize,
) -> i64 {
    -22
}

unsafe extern "C" fn application_close(_context: *mut core::ffi::c_void) {}

impl IhkSmpControlDevice {
    // PRODUCTION_NATIVE_IOCTL
    // PRODUCTION_COMPAT_IOCTL
}

fn reset(fault_after: Option<usize>) {
    COPY.with(|state| {
        *state.borrow_mut() = CopyState {
            fault_after,
            ..CopyState::default()
        };
    });
}

#[test]
fn native_copies_exact_consumer_buildid_and_trailing_nul() {
    reset(None);
    assert_eq!(
        IhkSmpControlDevice::ioctl(&ProviderOpenLease, 0x0011_290b, 0x1234),
        Ok(0)
    );
    COPY.with(|state| {
        let state = state.borrow();
        assert_eq!(state.address, 0x1234);
        assert_eq!(state.slice_length, b"fixture-id\0".len());
        assert_eq!(state.copied, b"fixture-id\0");
        assert_eq!(state.constructions, 1);
        assert_eq!(state.writes, 1);
    });
}

#[test]
fn native_preserves_full_width_address() {
    reset(None);
    let address = 0x0000_1234_5678_9000usize;
    assert_eq!(
        IhkSmpControlDevice::ioctl(&ProviderOpenLease, IHK_DEVICE_GET_BUILDID, address),
        Ok(0)
    );
    COPY.with(|state| assert_eq!(state.borrow().address, address));
}

#[test]
fn compat_zero_extends_the_low_32_bit_pointer() {
    for address in [0xffff_ffff_8000_1234usize, 0x1234_5678_0000_0000, 0x1234] {
        reset(None);
        assert_eq!(
            IhkSmpControlDevice::compat_ioctl(&ProviderOpenLease, IHK_DEVICE_GET_BUILDID, address),
            Ok(0)
        );
        COPY.with(|state| {
            let state = state.borrow();
            assert_eq!(state.address, address & 0xffff_ffff);
            assert_eq!(state.copied, b"fixture-id\0");
        });
    }
}

#[test]
fn unsupported_commands_do_not_construct_or_call_usercopy() {
    for cmd in [
        0,
        1,
        0x0011_290a,
        0x0011_ffff,
        0x8011_290b,
        u32::MAX,
    ] {
        reset(Some(0));
        assert_eq!(
            IhkSmpControlDevice::ioctl(&ProviderOpenLease, cmd, usize::MAX),
            Err(EINVAL)
        );
        assert_eq!(
            IhkSmpControlDevice::compat_ioctl(&ProviderOpenLease, cmd, usize::MAX),
            Err(EINVAL)
        );
        COPY.with(|state| {
            let state = state.borrow();
            assert_eq!(state.constructions, 0);
            assert_eq!(state.writes, 0);
            assert!(state.copied.is_empty());
        });
    }
}

#[test]
fn usercopy_fault_is_propagated_without_success_or_retry() {
    for compat in [false, true] {
        reset(Some(0));
        let result = if compat {
            IhkSmpControlDevice::compat_ioctl(&ProviderOpenLease, IHK_DEVICE_GET_BUILDID, 0)
        } else {
            IhkSmpControlDevice::ioctl(&ProviderOpenLease, IHK_DEVICE_GET_BUILDID, 0)
        };
        assert_eq!(result, Err(EFAULT));
        COPY.with(|state| {
            let state = state.borrow();
            assert_eq!(state.writes, 1);
            assert!(state.copied.is_empty());
        });
    }
}

#[test]
fn partial_mock_copy_fault_remains_efault_without_retry() {
    reset(Some(3));
    assert_eq!(
        IhkSmpControlDevice::ioctl(&ProviderOpenLease, IHK_DEVICE_GET_BUILDID, 0x1234),
        Err(EFAULT)
    );
    COPY.with(|state| {
        let state = state.borrow();
        assert_eq!(state.copied, b"fix");
        assert_eq!(state.writes, 1);
    });
}

#[test]
fn cpu_dispatch_preserves_native_address_and_compat_pointer_width() {
    let address = 0x1234_5678_8000_1234usize;
    for command in [cpu_abi::IHK_DEVICE_RESERVE_CPU, cpu_abi::IHK_DEVICE_RELEASE_CPU,
                    cpu_abi::IHK_DEVICE_GET_NUM_CPUS, cpu_abi::IHK_DEVICE_QUERY_CPU] {
        reset(Some(0));
        assert_eq!(IhkSmpControlDevice::ioctl(&ProviderOpenLease, command, address), Err(-16));
        CPU_CALL.with(|call| assert_eq!(*call.borrow(), Some((command, address, false))));
        assert_eq!(IhkSmpControlDevice::compat_ioctl(&ProviderOpenLease, command, address), Err(-16));
        CPU_CALL.with(|call| assert_eq!(*call.borrow(), Some((command, 0x8000_1234, true))));
        COPY.with(|state| assert_eq!(state.borrow().constructions, 0));
    }
}

#[test]
fn memory_dispatch_preserves_native_address_and_compat_pointer_width() {
    let address = 0x1234_5678_8000_1234usize;
    CPU_CALL.with(|call| *call.borrow_mut() = None);
    for command in [memory_abi::IHK_DEVICE_RESERVE_MEM, memory_abi::IHK_DEVICE_RELEASE_MEM,
                    memory_abi::IHK_DEVICE_QUERY_MEM, memory_abi::IHK_DEVICE_RELEASE_MEM_PARTIALLY] {
        reset(Some(0));
        assert_eq!(IhkSmpControlDevice::ioctl(&ProviderOpenLease, command, address), Err(-12));
        MEMORY_CALL.with(|call| assert_eq!(*call.borrow(), Some((command, address, false))));
        assert_eq!(IhkSmpControlDevice::compat_ioctl(&ProviderOpenLease, command, address), Err(-12));
        MEMORY_CALL.with(|call| assert_eq!(*call.borrow(), Some((command, 0x8000_1234, true))));
        CPU_CALL.with(|call| assert_eq!(*call.borrow(), None));
        COPY.with(|state| assert_eq!(state.borrow().constructions, 0));
    }
}
