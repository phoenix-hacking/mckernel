// SPDX-License-Identifier: GPL-2.0-only
//! Complete decoder and selected clone adapter with controlled VM/fork owners.

#[allow(dead_code)]
#[path = "abi.rs"]
mod abi;
#[path = "clone3.rs"]
mod clone3;
use abi::*;
use core::{
    ffi::c_void,
    mem::{offset_of, MaybeUninit},
    ptr::{addr_of, addr_of_mut, null_mut},
};
use std::cell::{Cell, RefCell};

thread_local! {
    static CURRENT: Cell<*mut Thread> = const { Cell::new(null_mut()) };
    static USER: RefCell<Vec<u8>> = const { RefCell::new(Vec::new()) };
    static RESULT: Cell<u64> = const { Cell::new(0) };
    static CALLS: RefCell<Vec<Vec<u64>>> = const { RefCell::new(Vec::new()) };
    static LOCKS: RefCell<Vec<(usize,usize,bool)>> = const { RefCell::new(Vec::new()) };
    static COPY_FAIL: Cell<bool> = const { Cell::new(false) };
}
unsafe fn current_thread_ptr() -> *mut Thread {
    CURRENT.with(Cell::get)
}
unsafe extern "C" fn syscall_copy_from_user_bridge(
    dst: *mut u8,
    address: u64,
    bytes: usize,
) -> i64 {
    if COPY_FAIL.with(Cell::get) {
        return -14;
    }
    USER.with(|user| {
        let user = user.borrow();
        let Some(offset) = address.checked_sub(0x100000) else {
            return -14;
        };
        let Some(end) = (offset as usize).checked_add(bytes) else {
            return -14;
        };
        if end > user.len() {
            return -14;
        }
        core::ptr::copy_nonoverlapping(user.as_ptr().add(offset as usize), dst, bytes);
        0
    })
}
unsafe extern "C" fn arch_clone_reader_lock_bridge(lock: *mut c_void, node: *mut c_void) {
    LOCKS.with(|log| log.borrow_mut().push((lock as usize, node as usize, true)));
}
unsafe extern "C" fn arch_clone_reader_unlock_bridge(lock: *mut c_void, node: *mut c_void) {
    LOCKS.with(|log| log.borrow_mut().push((lock as usize, node as usize, false)));
}
unsafe extern "C" fn do_fork(
    flags: i32,
    stack: u64,
    parent: u64,
    child: u64,
    tls: u64,
    pc: u64,
    sp: u64,
) -> u64 {
    CALLS.with(|calls| {
        calls
            .borrow_mut()
            .push(vec![flags as u32 as u64, stack, parent, child, tls, pc, sp])
    });
    RESULT.with(Cell::get)
}
include!("native-application-clone3-bodies.rs");

fn word(bytes: &[u8], index: usize) -> u64 {
    u64::from_le_bytes(bytes[index * 8..index * 8 + 8].try_into().unwrap())
}
fn copy_vector(
    address: u64,
    readable: u64,
    payload: &[u8],
    source: u64,
    target: &mut [u8],
) -> Result<(), i64> {
    let offset = source.checked_sub(address).ok_or(-14)?;
    let end = offset.checked_add(target.len() as u64).ok_or(-14)?;
    if source < 0x1000
        || source.checked_add(target.len() as u64).ok_or(-14)? > 0x800000000000
        || end > readable
    {
        return Err(-14);
    }
    target.copy_from_slice(&payload[offset as usize..end as usize]);
    Ok(())
}

#[test]
fn exact_linux_validation_and_explicit_unsupported_features() {
    let vectors = include_bytes!("vectors.bin");
    let lines: Vec<_> = include_str!("c-reference.log").lines().collect();
    assert_eq!(vectors.len(), lines.len() * 4128);
    assert!(lines.len() >= 300);
    for (index, (vector, line)) in vectors.chunks_exact(4128).zip(lines).enumerate() {
        let values: Vec<i128> = line
            .split_whitespace()
            .map(|value| value.parse().unwrap())
            .collect();
        assert_eq!(values[0], index as i128);
        let address = word(vector, 0);
        let size = word(vector, 1);
        let readable = word(vector, 2);
        let expected = word(vector, 3) as i64;
        let result = clone3::read(
            address,
            size as usize,
            0x1000,
            0x800000000000,
            |source, target| copy_vector(address, readable, &vector[32..], source, target),
        );
        if expected != -9999 {
            assert_eq!(
                values[1], 0,
                "unsupported vector {index} must otherwise be valid Linux input"
            );
            assert_eq!(result, Err(expected), "vector {index}");
        } else if values[1] != 0 {
            assert_eq!(result, Err(values[1] as i64), "vector {index}");
        } else {
            let result = result.unwrap_or_else(|error| panic!("vector {index}: {error}"));
            assert_eq!(
                vec![
                    result.flags,
                    result.stack,
                    result.parent_tid,
                    result.child_tid,
                    result.tls
                ],
                values[2..].iter().map(|v| *v as u64).collect::<Vec<_>>(),
                "vector {index}"
            );
        }
    }
}

#[test]
fn adapter_preserves_context_and_uses_actual_guest_clone_owner() {
    unsafe {
        let mut thread: Box<Thread> = Box::new(core::mem::zeroed());
        let mut process: Box<Process> = Box::new(core::mem::zeroed());
        let mut vm: Box<ProcessVm> = Box::new(core::mem::zeroed());
        vm.region.user_start = 0x1000;
        vm.region.user_end = 0x800000000000;
        thread.proc = &mut *process;
        thread.vm = &mut *vm;
        CURRENT.with(|p| p.set(&mut *thread));
        let mut ctx: X86UserContext = core::mem::zeroed();
        core::ptr::write_bytes(
            addr_of_mut!(ctx).cast::<u8>(),
            0x3d,
            core::mem::size_of_val(&ctx),
        );
        ctx.gpr.rdi = 0x100000;
        ctx.gpr.rsi = 88;
        ctx.gpr.rip = 0x4abcde;
        ctx.gpr.rsp = 0x700000;
        let before =
            core::slice::from_raw_parts(addr_of!(ctx).cast::<u8>(), core::mem::size_of_val(&ctx))
                .to_vec();
        for (flags, stack, parent, child, tls) in [
            (0x3d0f00u64, 0x300000u64, 0x301abc, 0x302abc, 0x3bc000),
            (0x3d0f00, 0x300000, 0x308000, 0x302abc, 0x3bc000),
            (0, 0, 0, 0, 0),
        ] {
            let mut bytes = vec![0; 88];
            for (index, value) in [
                (0, flags),
                (2, child),
                (3, parent),
                (4, if flags == 0 { 17 } else { 0 }),
                (5, stack),
                (6, if stack == 0 { 0 } else { 0x8000 }),
                (7, tls),
            ] {
                bytes[index * 8..index * 8 + 8].copy_from_slice(&value.to_le_bytes());
            }
            USER.with(|user| *user.borrow_mut() = bytes);
            for result in [321i64, -11, -12, -14, -22] {
                RESULT.with(|value| value.set(result as u64));
                CALLS.with(|calls| calls.borrow_mut().clear());
                LOCKS.with(|log| log.borrow_mut().clear());
                assert_eq!(sys_clone3(435, &mut ctx), result);
                let expected = vec![
                    flags | if flags == 0 { 17 } else { 0 },
                    if stack == 0 { 0 } else { stack + 0x8000 },
                    parent,
                    child,
                    tls,
                    0x4abcde,
                    0x700000,
                ];
                CALLS.with(|calls| assert_eq!(*calls.borrow(), vec![expected]));
                LOCKS.with(|log| {
                    let log = log.borrow();
                    assert_eq!(log.len(), 2);
                    assert_eq!(log[0].0, addr_of_mut!(process.coredump_lock) as usize);
                    assert_eq!(log[0].0, log[1].0);
                    assert_eq!(log[0].1, log[1].1);
                    assert!(log[0].2 && !log[1].2);
                });
                assert_eq!(
                    core::slice::from_raw_parts(addr_of!(ctx).cast::<u8>(), before.len()),
                    before
                );
            }
        }
        CURRENT.with(|p| p.set(null_mut()));
    }
}

#[test]
fn invalid_owners_copy_faults_and_arguments_never_create_a_thread() {
    unsafe {
        CALLS.with(|calls| calls.borrow_mut().clear());
        LOCKS.with(|log| log.borrow_mut().clear());
        assert_eq!(sys_clone3(435, null_mut()), -14);
        let mut ctx: X86UserContext = core::mem::zeroed();
        ctx.gpr.rdi = 0x100000;
        ctx.gpr.rsi = 88;
        assert_eq!(sys_clone3(435, &mut ctx), -14);
        let mut thread: Box<Thread> = Box::new(core::mem::zeroed());
        let mut proc: Box<Process> = Box::new(core::mem::zeroed());
        let mut vm: Box<ProcessVm> = Box::new(core::mem::zeroed());
        CURRENT.with(|p| p.set(&mut *thread));
        assert_eq!(sys_clone3(435, &mut ctx), -14);
        thread.proc = &mut *proc;
        assert_eq!(sys_clone3(435, &mut ctx), -14);
        vm.region.user_start = 0x1000;
        vm.region.user_end = 0x800000000000;
        thread.vm = &mut *vm;
        assert_eq!(sys_clone3(56, &mut ctx), -14);
        COPY_FAIL.with(|v| v.set(true));
        assert_eq!(sys_clone3(435, &mut ctx), -14);
        COPY_FAIL.with(|v| v.set(false));
        USER.with(|v| *v.borrow_mut() = vec![0; 88]);
        ctx.gpr.rsi = 63;
        assert_eq!(sys_clone3(435, &mut ctx), -22);
        ctx.gpr.rsi = 4097;
        assert_eq!(sys_clone3(435, &mut ctx), -7);
        ctx.gpr.rsi = 88;
        USER.with(|v| v.borrow_mut()[0..8].copy_from_slice(&0x1000u64.to_le_bytes()));
        assert_eq!(sys_clone3(435, &mut ctx), -95);
        CALLS.with(|calls| assert!(calls.borrow().is_empty()));
        LOCKS.with(|log| assert!(log.borrow().is_empty()));
        CURRENT.with(|p| p.set(null_mut()));
    }
}
