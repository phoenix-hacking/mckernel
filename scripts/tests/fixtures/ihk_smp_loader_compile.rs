//! Execute the production bounded file adapter against owned mock allocations.
#![allow(dead_code)]
extern crate self as kernel;
use std::sync::Mutex;

#[path = "../../../host-kernel/native-rust/smp_resource.rs"]
mod smp_resource;
#[path = "../../../host-kernel/native-rust/smp_loader.rs"]
mod smp_loader;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Error(i32);
pub type Result<T = ()> = std::result::Result<T, Error>;
pub const EINVAL: Error = Error(-22);
pub const EIO: Error = Error(-5);
pub mod prelude {
    pub use crate::{Error, Result, EINVAL, EIO};
}
pub mod error {
    pub fn to_result(value: i32) -> crate::Result {
        if value < 0 {
            Err(crate::Error(value))
        } else {
            Ok(())
        }
    }
}

#[derive(Default)]
struct State {
    name: Vec<u8>,
    reads: usize,
    fail_at: Option<usize>,
    calls: usize,
    result: isize,
    allocation: Option<Box<[u8]>>,
    frees: usize,
    invalidations: usize,
    loads: usize,
    null: bool,
}
static STATE: Mutex<State> = Mutex::new(State {
    name: Vec::new(),
    reads: 0,
    fail_at: None,
    calls: 0,
    result: 0,
    allocation: None,
    frees: 0,
    invalidations: 0,
    loads: 0,
    null: false,
});
static TEST: Mutex<()> = Mutex::new(());

pub mod uaccess {
    pub struct UserSlice {
        length: usize,
    }
    impl UserSlice {
        pub fn new(address: usize, length: usize) -> Self {
            assert_eq!(address, 0x1234);
            Self { length }
        }
        pub fn reader(self) -> Reader {
            Reader {
                offset: 0,
                length: self.length,
            }
        }
    }
    pub struct Reader {
        offset: usize,
        length: usize,
    }
    impl Reader {
        pub fn read<T: From<u8>>(&mut self) -> crate::Result<T> {
            let mut state = super::STATE.lock().unwrap();
            let index = self.offset;
            if index >= self.length || state.fail_at == Some(index) {
                return Err(crate::Error(-14));
            }
            let byte = *state.name.get(index).ok_or(crate::Error(-14))?;
            state.reads += 1;
            self.offset += 1;
            Ok(T::from(byte))
        }
    }
}

pub mod bindings {
    use core::ffi::{c_char, c_void};
    #[allow(non_upper_case_globals)]
    pub const kernel_read_file_id_READING_KEXEC_IMAGE: u32 = 3;
    pub unsafe fn kernel_read_file_from_path(
        name: *const c_char,
        offset: i64,
        buffer: *mut *mut c_void,
        maximum: usize,
        file_size: *mut usize,
        id: u32,
    ) -> isize {
        let mut state = super::STATE.lock().unwrap();
        assert!(unsafe { *buffer }.is_null());
        assert_eq!(offset, 0);
        assert_eq!(maximum, 64 << 20);
        assert!(file_size.is_null());
        assert_eq!(id, 3);
        let expected = state.name.split(|b| *b == 0).next().unwrap();
        assert_eq!(
            unsafe { std::ffi::CStr::from_ptr(name) }.to_bytes(),
            expected
        );
        state.calls += 1;
        if state.result >= 0 && !state.null {
            let mut bytes = vec![17_u8; 5].into_boxed_slice();
            unsafe { *buffer = bytes.as_mut_ptr().cast() };
            state.allocation = Some(bytes);
        }
        state.result
    }
    pub unsafe fn kvfree(buffer: *const c_void) {
        let mut state = super::STATE.lock().unwrap();
        let allocation = state.allocation.take().expect("one live vmalloc owner");
        assert_eq!(allocation.as_ptr().cast::<c_void>(), buffer);
        state.frees += 1;
    }
}

mod smp_memory {
    pub(super) fn invalidate_os_image(owner: super::smp_resource::OsToken) -> crate::Result {
        assert_eq!(owner.generation(), 7);
        super::STATE.lock().unwrap().invalidations += 1;
        Ok(())
    }
}
mod smp_cpu {
    pub(super) fn load_os_image(
        owner: super::smp_resource::OsToken,
        image: &[u8],
    ) -> crate::Result {
        assert_eq!(owner.generation(), 7);
        assert_eq!(image, &[17; 5]);
        let mut state = super::STATE.lock().unwrap();
        assert!(state.allocation.is_some());
        state.loads += 1;
        Ok(())
    }
}

#[test]
fn filename_stops_at_nul_and_file_owner_drops_after_load() {
    let _serial = TEST.lock().unwrap();
    for length in [0, 1, 254, 255] {
        let mut name = vec![b'x'; length];
        name.push(0);
        *STATE.lock().unwrap() = State {
            name,
            result: 5,
            ..Default::default()
        };
        assert_eq!(
            smp_loader::load(smp_resource::OsToken::test_only(2, 7).unwrap(), 0x1234),
            Ok(0)
        );
        let state = STATE.lock().unwrap();
        assert_eq!(
            (
                state.reads,
                state.calls,
                state.loads,
                state.frees,
                state.invalidations
            ),
            (length + 1, 1, 1, 1, 1)
        );
        assert!(state.allocation.is_none());
    }
}

#[test]
fn usercopy_failure_and_missing_terminator_never_open_a_file() {
    let _serial = TEST.lock().unwrap();
    for fail_at in [Some(0), Some(1), Some(255), None] {
        *STATE.lock().unwrap() = State {
            name: vec![b'x'; 256],
            fail_at,
            result: 5,
            ..Default::default()
        };
        let result = smp_loader::load(smp_resource::OsToken::test_only(2, 7).unwrap(), 0x1234);
        assert_eq!(
            result,
            Err(Error(if fail_at.is_some() { -14 } else { -22 }))
        );
        let state = STATE.lock().unwrap();
        assert_eq!(
            (state.calls, state.loads, state.frees, state.invalidations),
            (0, 0, 0, 1)
        );
    }
}

#[test]
fn linux_errors_propagate_and_invalid_return_shapes_cannot_reach_memory() {
    let _serial = TEST.lock().unwrap();
    for (result, null, error, frees) in [
        (-2, false, -2, 0),
        (-12, false, -12, 0),
        (-5, false, -5, 0),
        (-26, false, -26, 0),
        (-27, false, -27, 0),
        (0, false, -5, 1),
        ((64 << 20) + 1, false, -5, 1),
        (5, true, -5, 0),
    ] {
        *STATE.lock().unwrap() = State {
            name: b"image\0".to_vec(),
            result,
            null,
            ..Default::default()
        };
        assert_eq!(
            smp_loader::load(smp_resource::OsToken::test_only(2, 7).unwrap(), 0x1234),
            Err(Error(error))
        );
        let state = STATE.lock().unwrap();
        assert_eq!(
            (state.calls, state.loads, state.frees, state.invalidations),
            (1, 0, frees, 1)
        );
        assert!(state.allocation.is_none());
    }
}
