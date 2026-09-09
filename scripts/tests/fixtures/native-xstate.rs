// SPDX-License-Identifier: GPL-2.0-only
//! Pure copied-buffer policy tests. No XSAVE/XRSTOR instruction is executed.
#[path = "native_xstate.rs"]
mod native_xstate;

#[repr(C, align(64))]
struct State([u8; 832]);

fn state() -> State {
    let mut value = State([0; 832]);
    value.0[24..28].copy_from_slice(&0x1f80u32.to_le_bytes());
    value
}

#[test]
fn standard_saved_states_and_exact_size_contract() {
    for mask in [3u64, 7, 0xe7] {
        for active in 0..=mask {
            if active & !mask != 0 {
                continue;
            }
            let mut bytes = state();
            bytes.0[512..520].copy_from_slice(&active.to_le_bytes());
            assert_eq!(native_xstate::validate(&bytes.0, 832, mask, 0xffff), Ok(()));
            assert_eq!(
                unsafe {
                    native_xstate::native_xstate_validate_result(
                        bytes.0.as_ptr(),
                        832,
                        832,
                        mask,
                        0xffff,
                    )
                },
                0
            );
        }
    }
    for size in [-1, 0, 511, 512, 575, 65537, i32::MAX] {
        assert!(native_xstate::buffer_size(size, size).is_err());
    }
    for size in [576, 832, 4096, 65536] {
        assert_eq!(native_xstate::buffer_size(size, size), Ok(size as usize));
        assert_eq!(native_xstate::buffer_size(size, size + 1), Err(-22));
    }
}

#[test]
fn actual_cpu_mask_is_authoritative() {
    for bit in 0..32 {
        let mut bytes = state();
        let value = 1u32 << bit;
        bytes.0[24..28].copy_from_slice(&value.to_le_bytes());
        // User MXCSR_MASK bytes cannot enlarge the trusted hardware mask.
        bytes.0[28..32].copy_from_slice(&u32::MAX.to_le_bytes());
        assert_eq!(
            native_xstate::validate(&bytes.0, 832, 7, 0xffbf),
            if value & !0xffbf == 0 {
                Ok(())
            } else {
                Err(-22)
            }
        );
    }
    let mut bytes = state();
    bytes.0[24..28].copy_from_slice(&0x0040u32.to_le_bytes());
    assert_eq!(native_xstate::validate(&bytes.0, 832, 7, 0xffff), Ok(()));
    assert_eq!(native_xstate::validate(&bytes.0, 832, 7, 0xffbf), Err(-22));
}

#[test]
fn standard_header_subset_and_reserved_bytes() {
    for bit in 0..64 {
        let mut bytes = state();
        let active = 1u64 << bit;
        bytes.0[512..520].copy_from_slice(&active.to_le_bytes());
        assert_eq!(
            native_xstate::validate(&bytes.0, 832, 0xe7, 0xffff),
            if active & !0xe7 == 0 {
                Ok(())
            } else {
                Err(-22)
            }
        );
        bytes.0[512..520].fill(0);
        bytes.0[520..528].copy_from_slice(&active.to_le_bytes());
        assert_eq!(
            native_xstate::validate(&bytes.0, 832, 0xe7, 0xffff),
            Err(-22)
        );
    }
    for byte in 528..576 {
        let mut bytes = state();
        bytes.0[byte] = 1;
        assert_eq!(native_xstate::validate(&bytes.0, 832, 7, 0xffff), Err(-22));
    }
}
