use core::arch::asm;

use crate::abi::{CInt, CLong, TimeSpec, TimeVal, TodData};

const NR_GETTIMEOFDAY: CLong = 96;
const NR_TIME: CLong = 201;
const NR_GETCPU: CLong = 309;

extern "C" {
    fn calculate_time_from_tsc(ts: *mut TimeSpec);
}

#[no_mangle]
#[link_section = ".vsyscall.gettimeofday.data"]
pub static mut tod_data: TodData = TodData {
    do_local: 0,
    padding: [0; 7],
    version: crate::abi::IhkAtomic64 { counter64: 0 },
    clocks_per_sec: 0,
    origin: TimeSpec {
        tv_sec: 0,
        tv_nsec: 0,
    },
};

#[inline(always)]
unsafe fn raise_sigsegv_like_vsyscall() {
    unsafe {
        asm!("mov dword ptr [0], 0", options(nostack));
    }
}

#[no_mangle]
#[link_section = ".vsyscall.gettimeofday"]
pub unsafe extern "C" fn vsyscall_gettimeofday(tv: *mut TimeVal, tz: *mut u8) -> CInt {
    if tv.is_null() && tz.is_null() {
        return 0;
    }

    if tz.is_null() && unsafe { tod_data.do_local } != 0 {
        let mut ats = TimeSpec {
            tv_sec: 0,
            tv_nsec: 0,
        };
        unsafe {
            calculate_time_from_tsc(&raw mut ats);
            (*tv).tv_sec = ats.tv_sec;
            (*tv).tv_usec = ats.tv_nsec / 1000;
        }
        return 0;
    }

    let error: CLong;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") NR_GETTIMEOFDAY => error,
            in("rdi") tv,
            in("rsi") tz,
            lateout("rcx") _,
            lateout("r11") _,
            options(nostack)
        );
    }

    if error != 0 {
        unsafe {
            raise_sigsegv_like_vsyscall();
        }
    }
    error as CInt
}

#[no_mangle]
#[link_section = ".vsyscall.time"]
pub unsafe extern "C" fn vsyscall_time(tp: *mut CLong) -> CLong {
    let t: CLong;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") NR_TIME => t,
            in("rdi") 0usize,
            lateout("rcx") _,
            lateout("r11") _,
            options(nostack)
        );
        if !tp.is_null() {
            *tp = t;
        }
    }
    t
}

#[no_mangle]
#[link_section = ".vsyscall.getcpu"]
pub unsafe extern "C" fn vsyscall_getcpu(
    cpup: *mut u32,
    nodep: *mut u32,
    tcachep: *mut u8,
) -> CInt {
    let error: CLong;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") NR_GETCPU => error,
            in("rdi") cpup,
            in("rsi") nodep,
            in("rdx") tcachep,
            lateout("rcx") _,
            lateout("r11") _,
            options(nostack)
        );
    }
    error as CInt
}
