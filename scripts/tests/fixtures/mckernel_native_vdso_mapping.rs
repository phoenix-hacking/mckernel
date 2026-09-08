// Included after the complete production Rust mapping bodies by the fixture.
use std::sync::{
    atomic::{AtomicI32, Ordering},
    Mutex,
};

#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Outcome {
    error: i32,
    count: u32,
    map_end: u64,
    vdso_addr: u64,
    vvar_addr: u64,
    calls: [[u64; 6]; 16],
}
impl Outcome {
    const fn new() -> Self {
        Self {
            error: 0,
            count: 0,
            map_end: 0,
            vdso_addr: 0,
            vvar_addr: 0,
            calls: [[0; 6]; 16],
        }
    }
}
static TRACE: Mutex<Outcome> = Mutex::new(Outcome::new());
static FAIL: AtomicI32 = AtomicI32::new(0);

fn record_call(row: [u64; 6]) -> CInt {
    let mut trace = TRACE.lock().unwrap();
    let index = trace.count as usize;
    trace.calls[index] = row;
    trace.count += 1;
    if trace.count as i32 == FAIL.load(Ordering::Relaxed) {
        -12
    } else {
        0
    }
}
unsafe extern "C" fn add_range(
    _vm: *mut ProcessVm,
    start: u64,
    end: u64,
    flags: u64,
    range: *mut *mut VmRange,
) -> CInt {
    unsafe { *range = 0x1000 as *mut VmRange };
    record_call([1, start, end, 0, flags, 0])
}
unsafe extern "C" fn set_range(
    _pt: *mut c_void,
    _vm: *mut ProcessVm,
    start: u64,
    end: u64,
    physical: u64,
    attr: u64,
    _range: *mut VmRange,
) -> CInt {
    record_call([2, start, end, physical, attr, 0])
}
fn run_map(vdso: &ArchVdso, extras: &[(isize, u64)], failure: i32) -> Outcome {
    *TRACE.lock().unwrap() = Outcome::new();
    FAIL.store(failure, Ordering::Relaxed);
    let mut vm: ProcessVm = unsafe { core::mem::zeroed() };
    vm.region.map_end = 0x100000;
    let (size, offset) = arch_vdso_container(vdso);
    let error = unsafe {
        arch_map_vdso_with_pages(
            &mut vm,
            0x4000 as *mut c_void,
            vdso,
            size,
            offset,
            Some(add_range),
            Some(set_range),
            None,
            extras,
        )
    };
    let mut outcome = *TRACE.lock().unwrap();
    outcome.error = error;
    outcome.map_end = vm.region.map_end;
    outcome.vdso_addr = vm.vdso_addr as u64;
    outcome.vvar_addr = vm.vvar_addr as u64;
    outcome
}

extern "C" {
    fn reference_map(
        vdso: *const ArchVdso,
        size: usize,
        offset: isize,
        failure: i32,
        output: *mut Outcome,
    );
}

#[test]
fn existing_c_map_body_matches_rust_with_no_supplemental_pages() {
    let mut scenarios = 0;
    for pages in [1, 2] {
        for globals in 0..8 {
            let vdso = ArchVdso {
                busy: 0,
                vdso_npages: pages,
                vvar_is_global: globals & 1,
                hpet_is_global: (globals >> 1) & 1,
                pvti_is_global: (globals >> 2) & 1,
                padding: 0,
                vdso_physlist: [0x2000, 0x3000],
                vvar_virt: (-12288_isize) as *mut c_void,
                vvar_phys: 0x4000,
                hpet_virt: (-8192_isize) as *mut c_void,
                hpet_phys: 0x5000,
                pvti_virt: (-4096_isize) as *mut c_void,
                pvti_phys: 0x6000,
                vgtod_virt: null_mut(),
            };
            let (size, offset) = arch_vdso_container(&vdso);
            for failure in 0..9 {
                let rust = run_map(&vdso, &[], failure);
                let mut reference = Outcome::new();
                unsafe { reference_map(&vdso, size, offset, failure, &mut reference) };
                assert_eq!(
                    rust, reference,
                    "pages={pages} globals={globals} failure={failure}"
                );
                scenarios += 1;
            }
        }
    }
    println!("actual C/Rust mapping scenarios={scenarios}");
}

#[test]
fn native_generic_pages_preserve_holes_cache_attributes_and_failure_order() {
    let vdso = ArchVdso {
        busy: 0,
        vdso_npages: 2,
        vvar_is_global: 0,
        hpet_is_global: 0,
        pvti_is_global: 0,
        padding: 0,
        vdso_physlist: [0x2000, 0x3000],
        vvar_virt: (-24576_isize) as *mut c_void,
        vvar_phys: 0x4000,
        hpet_virt: null_mut(),
        hpet_phys: 0,
        pvti_virt: null_mut(),
        pvti_phys: 0,
        vgtod_virt: null_mut(),
    };
    for optional in 0..4 {
        let extras = [
            (-16384, 0x5000),
            (-8192, if optional & 1 != 0 { 0x6000 } else { 0 }),
            (-4096, if optional & 2 != 0 { 0x7000 } else { 0 }),
        ];
        let trace = run_map(&vdso, &extras, 0);
        assert_eq!(
            (trace.error, trace.map_end, trace.vdso_addr, trace.vvar_addr),
            (0, 0x108000, 0x106000, 0x100000)
        );
        let mapped: Vec<_> = trace.calls[..trace.count as usize]
            .iter()
            .copied()
            .filter(|row| row[0] == 2)
            .collect();
        let mut expected = vec![
            (0x106000, 0x2000, 5),
            (0x107000, 0x3000, 5),
            (0x102000, 0x5000, 0x8000000000000005),
        ];
        if optional & 1 != 0 {
            expected.push((0x104000, 0x6000, 0x8000000000000005));
        }
        if optional & 2 != 0 {
            expected.push((0x105000, 0x7000, 0x8000000000000005));
        }
        expected.push((0x100000, 0x4000, 0x8000000000000005));
        assert_eq!(
            mapped,
            expected
                .iter()
                .map(|&(s, p, a)| [2, s, s + 4096, p, a, 0])
                .collect::<Vec<_>>()
        );
        for failure in 1..=trace.count {
            let failed = run_map(&vdso, &extras, failure as i32);
            assert_eq!((failed.error, failed.count), (-12, failure));
            assert_eq!(
                &failed.calls[..failure as usize],
                &trace.calls[..failure as usize]
            );
        }
    }
    for bad in [
        vec![(-16383, 0x5000)],
        vec![(-28672, 0x5000)],
        vec![(0, 0x5000)],
        vec![(-16384, 0x5001)],
        vec![(-24576, 0x5000)],
        vec![(-16384, 256 << 30)],
        vec![(-16384, 0x5000), (-16384, 0x6000)],
    ] {
        let outcome = run_map(&vdso, &bad, 0);
        assert_eq!(
            (outcome.error, outcome.count, outcome.map_end),
            (-22, 0, 0x100000)
        );
    }
}
