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
}

mod kernel {
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

struct ProviderOpenLease;
struct IhkSmpControlDevice;

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
        0x0011_2900,
        0x0011_2901,
        0x0011_290a,
        0x0011_290c,
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
