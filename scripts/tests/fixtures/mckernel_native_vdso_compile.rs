#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/abi/vdso.rs"]
mod wire;
#[path = "../../../host-kernel/native-rust/ihk_mapping.rs"]
mod ihk_mapping;

use core::cell::UnsafeCell;
use core::ptr::{addr_of_mut, copy_nonoverlapping};
use std::sync::Arc;
use wire::{Descriptor, Error};

fn response() -> Descriptor {
    Descriptor::response(
        2,
        [0x2974000, 0x2975000],
        [0x3006000, 0, 0x3007000, 0, 0x3100000, 0x3200000],
    )
    .unwrap()
}

#[test]
fn request_response_encoding_and_negative_fields() {
    let request = Descriptor::request();
    assert_eq!(Descriptor::decode(&request.encode()), request);
    assert_eq!(
        &request.encode()[8..20],
        &[1, 0, 0, 0, 128, 0, 0, 0, 141, 255, 255, 255]
    );
    assert_eq!(request.validate_response(), Err(Error::InProgress));
    let good = response();
    assert_eq!(Descriptor::decode(&good.encode()), good);
    for offset in [
        0, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120,
    ] {
        let mut encoded = good.encode();
        encoded[offset] ^= 1;
        assert!(
            Descriptor::decode(&encoded).validate_response().is_err(),
            "offset={offset}"
        );
    }
    for index in 0..8 {
        let mut bad = good;
        let slot = if index < 2 {
            &mut bad.text_physical[index]
        } else {
            &mut bad.data_physical[index - 2]
        };
        *slot = wire::PHYSICAL_LIMIT;
        assert!(bad.validate_response().is_err());
    }
    let mut bad = good;
    bad.data_physical[2] = bad.text_physical[0];
    assert_eq!(bad.validate_response(), Err(Error::Pages));
    assert!(Descriptor::response(1, [4096, 0], [8192, 0, 12288, 0, 0, 0]).is_ok());
    assert!(Descriptor::response(1, [4096, 8192], [12288, 0, 16384, 0, 0, 0]).is_err());
}

#[repr(C, align(4096))]
struct Storage(UnsafeCell<[u8; 8192]>);
// This fixture uses exactly the one-shot cross-kernel publication protocol.
unsafe impl Sync for Storage {}

#[test]
fn concurrent_cross_page_completion_preserves_canaries_and_all_fields() {
    for iteration in 0..128 {
        let storage = Arc::new(Storage(UnsafeCell::new([0xa5; 8192])));
        let offset = 4096 - 64;
        let destination = unsafe { storage.0.get().cast::<u8>().add(offset) };
        unsafe {
            copy_nonoverlapping(
                Descriptor::request().encode().as_ptr(),
                destination,
                wire::BYTES,
            )
        };
        assert_eq!(
            unsafe { wire::read_response(destination) },
            Err(Error::InProgress)
        );
        let mut expected = response();
        expected.text_physical[0] += iteration * 8192;
        expected.text_physical[1] += iteration * 8192;
        let host = storage.clone();
        let thread = std::thread::spawn(move || unsafe {
            wire::complete(host.0.get().cast::<u8>().add(offset), &expected).unwrap();
        });
        loop {
            match unsafe { wire::read_response(destination) } {
                Ok(actual) => {
                    assert_eq!(actual, expected);
                    break;
                }
                Err(Error::InProgress) => std::hint::spin_loop(),
                failure => panic!("partial reply: {failure:?}"),
            }
        }
        thread.join().unwrap();
        let bytes = unsafe { &*storage.0.get() };
        assert!(bytes[..offset].iter().all(|&byte| byte == 0xa5));
        assert!(bytes[offset + wire::BYTES..]
            .iter()
            .all(|&byte| byte == 0xa5));
        assert_eq!(
            unsafe { wire::complete(destination, &expected) },
            Err(Error::Request)
        );
    }
}

#[test]
fn malformed_request_and_reply_never_publish_or_write() {
    #[repr(align(8))]
    struct Aligned([u8; wire::BYTES]);
    for index in 0..wire::BYTES {
        let mut storage = Aligned(Descriptor::request().encode());
        storage.0[index] ^= 1;
        let before = storage.0;
        assert!(unsafe { wire::complete(storage.0.as_mut_ptr(), &response()) }.is_err());
        assert_eq!(storage.0, before);
    }
    let mut storage = Aligned(Descriptor::request().encode());
    let before = storage.0;
    let mut invalid = response();
    invalid.text_pages = 0;
    assert!(unsafe { wire::complete(storage.0.as_mut_ptr(), &invalid) }.is_err());
    assert_eq!(storage.0, before);
    assert_eq!(
        unsafe { wire::complete(storage.0.as_mut_ptr().add(1), &response()) },
        Err(Error::Alignment)
    );
}

fn time_data() -> Box<wire::TimeData> {
    Box::new(unsafe { core::mem::zeroed() })
}

#[test]
fn actual_clock_modes_coarse_raw_rollover_and_sequence_retry() {
    let mut data = time_data();
    data.clock_data[0].basetime[5] = wire::Timestamp {
        sec: 100,
        nsec: 999_999_999,
    };
    assert_eq!(
        unsafe { wire::read_clock(&*data, 5, || panic!("coarse needs no TSC")) },
        Some((100, 999_999_999))
    );
    for mode in [
        wire::CLOCK_NONE,
        wire::CLOCK_PVCLOCK,
        wire::CLOCK_HVCLOCK,
        i32::MAX,
    ] {
        data.clock_data[0].clock_mode = mode;
        assert_eq!(
            unsafe { wire::read_clock(&*data, 0, || panic!("unsupported counter")) },
            None
        );
    }
    for clock_id in [0, 1, 4, 7, 11] {
        let clock = &mut data.clock_data[(clock_id == 4) as usize];
        clock.clock_mode = wire::CLOCK_TSC;
        clock.cycle_last = 10;
        clock.max_cycles = 1_000_000_000;
        clock.mult = 2;
        clock.shift = 1;
        clock.basetime[clock_id] = wire::Timestamp {
            sec: 1000 + clock_id as u64,
            nsec: 1_999_999_998,
        };
        assert_eq!(
            unsafe { wire::read_clock(&*data, clock_id as i32, || 13) },
            Some((1001 + clock_id as i64, 2))
        );
    }
    let pointer: *mut wire::TimeData = &mut *data;
    let mut attempts = 0;
    let sample = unsafe {
        wire::read_clock(pointer, 0, || {
            attempts += 1;
            if attempts == 1 {
                addr_of_mut!((*pointer).clock_data[0].basetime[0].sec).write_volatile(2000);
                addr_of_mut!((*pointer).clock_data[0].seq).write_volatile(2);
            }
            13
        })
    };
    assert_eq!(attempts, 2);
    assert_eq!(sample, Some((2001, 2)));
    data.clock_data[0].seq = 3;
    assert_eq!(unsafe { wire::read_clock(&*data, 5, || 0) }, None);
    assert_eq!(unsafe { wire::read_clock(&*data, 2, || 0) }, None);
}

#[test]
fn exact_linux_address_geometry_rejects_other_mappings_and_overflow() {
    use ihk_mapping::{kernel_image_physical as image, kernel_linear_physical as linear};
    assert_eq!(
        image(0xffffffff82974000, 0, wire::PHYSICAL_LIMIT),
        Some(0x2974000)
    );
    assert_eq!(
        image(0xffffffff82974000, 0x200000, wire::PHYSICAL_LIMIT),
        Some(0x2b74000)
    );
    for address in [0xffffffff7fffffff, 0xffffffffc0000000, u64::MAX, 0] {
        assert_eq!(image(address, 0, wire::PHYSICAL_LIMIT), None);
    }
    assert_eq!(
        image(0xffffffff82974000, u64::MAX, wire::PHYSICAL_LIMIT),
        None
    );
    let base = 0xffff888000000000;
    assert_eq!(
        linear(base + 0x3006000, base, wire::PHYSICAL_LIMIT),
        Some(0x3006000)
    );
    assert_eq!(linear(base - 1, base, wire::PHYSICAL_LIMIT), None);
    assert_eq!(
        linear(base + wire::PHYSICAL_LIMIT, base, wire::PHYSICAL_LIMIT),
        None
    );
}

#[cfg(linux_clock_reference)]
extern "C" {
    fn reference_ns(cycles: u64, last: u64, max: u64, mult: u32, shift: u32, base: u64) -> u64;
}

#[cfg(linux_clock_reference)]
#[test]
fn exact_pinned_linux_clock_arithmetic_matches_boundary_and_random_cases() {
    let values = [
        0,
        1,
        1 << 31,
        (1 << 32) - 1,
        1 << 32,
        (1 << 62) - 1,
        1 << 62,
        i64::MAX as u64,
    ];
    let mut checked = 0;
    for cycles in values {
        for last in values {
            for max in values {
                for shift in [0, 1, 10, 24, 32, 63] {
                    for mult in [0, 1, 12345, u32::MAX] {
                        let base = u64::MAX - last;
                        assert_eq!(
                            wire::tsc_nanoseconds(cycles, last, max, mult, shift, base),
                            Some(unsafe { reference_ns(cycles, last, max, mult, shift, base) })
                        );
                        checked += 1;
                    }
                }
            }
        }
    }
    let mut seed = 0x9212345678abcdef_u64;
    let mut random = || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed
    };
    for _ in 0..65536 {
        let (cycles, last, max, mult, shift, base) = (
            random() & i64::MAX as u64,
            random(),
            random(),
            random() as u32,
            random() as u32 % 64,
            random(),
        );
        assert_eq!(
            wire::tsc_nanoseconds(cycles, last, max, mult, shift, base),
            Some(unsafe { reference_ns(cycles, last, max, mult, shift, base) })
        );
        checked += 1;
    }
    assert_eq!(wire::tsc_nanoseconds(0, 0, 0, 1, 64, 0), None);
    assert_eq!(wire::tsc_nanoseconds(u64::MAX, 0, 0, 1, 0, 0), None);
    println!("exact Linux clock cases={checked}");
}
