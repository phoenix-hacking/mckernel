"""Actual Rust/C ptrace-regset behavior must use the configured XSAVE extent.

This isolated unit fixture includes production abi.rs and the complete selected
xstate copy modules. It extracts the eligible public regset wrappers/bodies and
C fallbacks verbatim. Only copy/CPU-size/unused diagnostic or GP-register effects
are unit-test observation doubles. No XSAVE/XRSTOR or kernel/native execution is
performed, and successful fixture linkage is not production link acceptance.

The length rule follows Linux ptrace_regset and x86_64 regset element sizes:
https://github.com/torvalds/linux/blob/master/kernel/ptrace.c
https://github.com/torvalds/linux/blob/master/arch/x86/kernel/ptrace.c
Both supported regsets have eight-byte elements; validate before clamping.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def item(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


RUST_DOUBLES = r'''
use core::{ffi::c_void, mem::{offset_of, size_of, MaybeUninit}};
use abi::{CInt, CLong, CULong, SizeT, Iovec, UserRegsStruct, XsaveStruct, Thread};
use std::sync::atomic::{AtomicI32, AtomicUsize, Ordering};
static CONFIGURED: AtomicI32 = AtomicI32::new(0);
static COPY_ERROR: AtomicI32 = AtomicI32::new(0);
static COPY_BYTES: AtomicUsize = AtomicUsize::new(usize::MAX);
mod x86_cpu_helpers {
    pub unsafe extern "C" fn get_xsave_size() -> i32 {
        super::CONFIGURED.load(super::Ordering::Relaxed)
    }
}
mod x86_memory_helpers {
    use super::*;
    pub unsafe extern "C" fn copy_to_user(dst: *mut c_void, src: *const c_void,
                                         bytes: usize) -> i32 {
        COPY_BYTES.store(bytes, Ordering::Relaxed);
        let result = COPY_ERROR.load(Ordering::Relaxed);
        if result == 0 { unsafe { core::ptr::copy_nonoverlapping(src.cast::<u8>(), dst.cast::<u8>(), bytes) }; }
        result
    }
    pub unsafe extern "C" fn copy_from_user(dst: *mut c_void, src: *const c_void,
                                           bytes: usize) -> i32 {
        unsafe { copy_to_user(dst, src, bytes) }
    }
}
const EFAULT: i32 = 14;
const EINVAL: i32 = 22;
const NT_PRSTATUS: i64 = 1;
const NT_X86_XSTATE: i64 = 0x202;
const ARCH_PTRACE_REGSET_LOG_READ_UNSUPPORTED: i32 = 1;
const ARCH_PTRACE_REGSET_LOG_WRITE_UNSUPPORTED: i32 = 2;
type ArchPtraceGpregsReadFn = unsafe extern "C" fn(u64, *mut u8) -> i64;
type ArchPtraceGpregsWriteFn = unsafe extern "C" fn(u64, *const u8) -> i64;
type PtraceUserCopyToFn = unsafe extern "C" fn(u64, *const u8, usize) -> i64;
type PtraceUserCopyFromFn = unsafe extern "C" fn(*mut u8, u64, usize) -> i64;
type ArchPtraceXstateIoFn = unsafe extern "C" fn(u64, u64, usize) -> i64;
type ArchPtraceRegsetLogFn = unsafe extern "C" fn(i32, i64);
unsafe extern "C" fn arch_ptrace_read_gpregs_bridge(_:u64, _: *mut u8) -> i64 { -999 }
unsafe extern "C" fn arch_ptrace_write_gpregs_bridge(_:u64, _: *const u8) -> i64 { panic!("unexpected GP write") }
unsafe extern "C" fn arch_copy_to_user_bridge(_:u64, _: *const u8, _:usize) -> i64 { panic!("unexpected GP copy") }
unsafe extern "C" fn arch_copy_from_user_bridge(_: *mut u8, _:u64, _:usize) -> i64 { panic!("unexpected GP copy") }
unsafe extern "C" fn arch_ptrace_regset_log_bridge(_:i32, _:i64) { panic!("unexpected unsupported type") }
use f06_ptrace_xstate_copy_to::arch_ptrace_xstate_copy_to_bridge;
use f06_ptrace_xstate_copy_from::arch_ptrace_xstate_copy_from_bridge;
'''

RUST_CASES = r'''
#[test]
fn actual_wrappers_use_boot_extent_for_read_and_write() {
    let mut thread = MaybeUninit::<Thread>::zeroed();
    let target = thread.as_mut_ptr();
    for configured in [576usize, 832, 2688, 11008] {
        CONFIGURED.store(configured as i32, Ordering::Relaxed);
        for requested in [0usize, 48, configured, usize::MAX & !7] {
            for writing in [false, true] {
                for error in [0i32, -4095] {
                    // The complete buffer includes guards beyond every admitted
                    // configured extent; no actual hardware instruction is used.
                    let mut fp = vec![0xc3u8; 16384];
                    let mut user = vec![0x5au8; 16384];
                    for index in 0..configured {
                        fp[index] = index.wrapping_mul(7) as u8;
                        user[index] = !(index.wrapping_mul(13) as u8);
                    }
                    let old_fp = fp.clone();
                    let old_user = user.clone();
                    unsafe { core::ptr::addr_of_mut!((*target).fp_regs).write(fp.as_mut_ptr().cast()) };
                    let mut iov = Iovec { iov_base: user.as_mut_ptr().cast(), iov_len: requested };
                    COPY_ERROR.store(error, Ordering::Relaxed);
                    COPY_BYTES.store(usize::MAX, Ordering::Relaxed);
                    let result = unsafe {
                        if writing { ptrace_write_regset(target, NT_X86_XSTATE, &mut iov) }
                        else { ptrace_read_regset(target, NT_X86_XSTATE, &mut iov) }
                    };
                    let copied = requested.min(configured);
                    assert_eq!(result, error as i64, "signed copy result");
                    assert_eq!(iov.iov_len, copied, "configured={configured} requested={requested} write={writing}");
                    assert_eq!(COPY_BYTES.load(Ordering::Relaxed), copied);
                    if error != 0 {
                        assert_eq!(fp, old_fp);
                        assert_eq!(user, old_user);
                    } else if writing {
                        assert_eq!(&fp[..copied], &old_user[..copied]);
                        assert_eq!(&fp[copied..], &old_fp[copied..]);
                        assert_eq!(user, old_user);
                    } else {
                        assert_eq!(&user[..copied], &old_fp[..copied]);
                        assert_eq!(&user[copied..], &old_user[copied..]);
                        assert_eq!(fp, old_fp);
                    }
                }
            }
        }
    }
    unsafe { core::ptr::addr_of_mut!((*target).fp_regs).write(core::ptr::null_mut()) };
    for writing in [false, true] {
        COPY_BYTES.store(usize::MAX, Ordering::Relaxed);
        let mut iov = Iovec { iov_base: core::ptr::null_mut(), iov_len: 8 };
        let result = unsafe {
            if writing { ptrace_write_regset(target, NT_X86_XSTATE, &mut iov) }
            else { ptrace_read_regset(target, NT_X86_XSTATE, &mut iov) }
        };
        assert_eq!(result, -12);
        assert_eq!(COPY_BYTES.load(Ordering::Relaxed), usize::MAX);
    }
}
#[test]
fn nonintegral_register_lengths_fail_before_provider_or_length_changes() {
    let mut thread = MaybeUninit::<Thread>::zeroed();
    let target = thread.as_mut_ptr();
    let mut fp = [0xa5u8; 16384];
    let mut user = [0x5au8; 16384];
    unsafe { core::ptr::addr_of_mut!((*target).fp_regs).write(fp.as_mut_ptr().cast()) };
    CONFIGURED.store(832, Ordering::Relaxed);
    COPY_ERROR.store(0, Ordering::Relaxed);
    for type_ in [NT_PRSTATUS, NT_X86_XSTATE] {
        for requested in [1usize, 7, 9, 215, 217, 833, usize::MAX] {
            for writing in [false, true] {
                COPY_BYTES.store(usize::MAX, Ordering::Relaxed);
                let mut iov = Iovec { iov_base: user.as_mut_ptr().cast(), iov_len: requested };
                let result = unsafe {
                    if writing { ptrace_write_regset(target, type_, &mut iov) }
                    else { ptrace_read_regset(target, type_, &mut iov) }
                };
                assert_eq!(result, -22, "type={type_} requested={requested} write={writing}");
                assert_eq!(iov.iov_len, requested);
                assert_eq!(COPY_BYTES.load(Ordering::Relaxed), usize::MAX);
                assert!(fp.iter().all(|byte| *byte == 0xa5));
                assert!(user.iter().all(|byte| *byte == 0x5a));
            }
        }
    }
}
'''

C_DOUBLES = r'''
#include <errno.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/uio.h>
#define NT_PRSTATUS 1
#define NT_X86_XSTATE 0x202
/* These local observation-provider objects never cross the C/Rust boundary. */
struct thread { fp_regs_struct *fp_regs; };
static int configured_size, copy_error;
static size_t copy_bytes;
int get_xsave_size(void) { return configured_size; }
int copy_to_user(void *dst, const void *src, size_t bytes) {
    copy_bytes=bytes;
    if (!copy_error) memcpy(dst,src,bytes);
    return copy_error;
}
int copy_from_user(void *dst, const void *src, size_t bytes) {
    return copy_to_user(dst,src,bytes);
}
int kprintf(const char *format, ...) { (void)format; return 0; }
long ptrace_read_gpregs(struct thread *thread, struct user_regs_struct *regs) {
    (void)thread; (void)regs; return -999;
}
long ptrace_write_gpregs(struct thread *thread, const struct user_regs_struct *regs) {
    (void)thread; (void)regs; return -999;
}
'''

C_CASES = r'''
int main(void) {
    const size_t sizes[]={576,832,2688,11008};
    for (unsigned s=0;s<4;s++) {
        configured_size=(int)sizes[s];
        const size_t requests[]={0,48,sizes[s],SIZE_MAX & ~(size_t)7};
        for (unsigned r=0;r<4;r++) for (unsigned writing=0;writing<2;writing++)
        for (unsigned failure=0;failure<2;failure++) {
            _Alignas(64) unsigned char fp[16384],user[16384],old_fp[16384],old_user[16384];
            memset(fp,0xc3,sizeof fp); memset(user,0x5a,sizeof user);
            for (size_t i=0;i<sizes[s];i++) { fp[i]=(unsigned char)(i*7); user[i]=(unsigned char)~(i*13); }
            memcpy(old_fp,fp,sizeof fp); memcpy(old_user,user,sizeof user);
            struct thread thread={.fp_regs=(fp_regs_struct *)fp};
            struct iovec iov={.iov_base=user,.iov_len=requests[r]};
            copy_error=failure ? -4095 : 0; copy_bytes=SIZE_MAX;
            long result=writing ? ptrace_write_regset(&thread,NT_X86_XSTATE,&iov)
                                : ptrace_read_regset(&thread,NT_X86_XSTATE,&iov);
            size_t expected=requests[r]<sizes[s] ? requests[r] : sizes[s];
            if (result!=copy_error || iov.iov_len!=expected || copy_bytes!=expected) {
                fprintf(stderr,"C extent failure configured=%d requested=%zu write=%u len=%zu copy=%zu expected=%zu result=%ld\n",
                        configured_size,requests[r],writing,iov.iov_len,copy_bytes,expected,result);
                return 1;
            }
            const unsigned char *want_fp=writing && !copy_error ? old_user : old_fp;
            const unsigned char *want_user=!writing && !copy_error ? old_fp : old_user;
            if (memcmp(fp,want_fp,expected) || memcmp(user,want_user,expected) ||
                memcmp(fp+expected,old_fp+expected,sizeof fp-expected) ||
                memcmp(user+expected,old_user+expected,sizeof user-expected)) return 2;
        }
    }
    struct thread missing={.fp_regs=NULL};
    struct iovec iov={.iov_base=NULL,.iov_len=8};
    copy_bytes=SIZE_MAX;
    if (ptrace_read_regset(&missing,NT_X86_XSTATE,&iov)!=-ENOMEM ||
        ptrace_write_regset(&missing,NT_X86_XSTATE,&iov)!=-ENOMEM || copy_bytes!=SIZE_MAX) return 3;
    const long types[]={NT_PRSTATUS,NT_X86_XSTATE};
    const size_t invalid[]={1,7,9,215,217,833,SIZE_MAX};
    unsigned char fp[16384],user[16384];
    memset(fp,0xa5,sizeof fp); memset(user,0x5a,sizeof user);
    struct thread thread={.fp_regs=(fp_regs_struct *)fp};
    configured_size=832; copy_error=0;
    for (unsigned t=0;t<2;t++) for (unsigned r=0;r<7;r++) for (unsigned writing=0;writing<2;writing++) {
        iov.iov_base=user; iov.iov_len=invalid[r]; copy_bytes=SIZE_MAX;
        long result=writing ? ptrace_write_regset(&thread,types[t],&iov)
                            : ptrace_read_regset(&thread,types[t],&iov);
        if (result!=-EINVAL || iov.iov_len!=invalid[r] || copy_bytes!=SIZE_MAX) {
            fprintf(stderr,"C invalid regset length accepted type=%ld requested=%zu write=%u result=%ld\n",
                    types[t],invalid[r],writing,result);
            return 4;
        }
        for (size_t i=0;i<sizeof fp;i++) if (fp[i]!=0xa5 || user[i]!=0x5a) return 5;
    }
    puts("C configured-xstate read/write cases passed");
    return 0;
}
'''


class F06XstateExtentTests(unittest.TestCase):
    def run_checked(self, argv):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_actual_rust_and_c_configured_extent(self):
        rustc = os.environ.get("RUSTC") or shutil.which("rustc")
        cc = shutil.which("gcc")
        if not rustc or not cc:
            self.skipTest("rustc and GCC are required for the isolated ABI fixture")
        rust = (ROOT / "kernel/rust/syscall_policy.rs").read_text()
        c = (ROOT / "arch/x86_64/kernel/syscall.c").read_text()
        registers = (ROOT / "arch/x86_64/kernel/include/registers.h").read_text()
        process = (ROOT / "kernel/include/process.h").read_text()
        with tempfile.TemporaryDirectory(prefix="m14-f06-xstate-") as tmp:
            out = Path(tmp)
            prefix = "#![allow(dead_code, unused_imports)]\n"
            for module in ("abi", "f06_ptrace_xstate_copy_to", "f06_ptrace_xstate_copy_from"):
                prefix += f"#[path={json.dumps(str(ROOT / 'kernel/rust' / (module + '.rs')))}] mod {module};\n"
            signatures = ["pub unsafe extern \"C\" fn ptrace_read_regset(",
                          "pub unsafe extern \"C\" fn ptrace_write_regset(",
                          "pub unsafe extern \"C\" fn arch_ptrace_read_regset_body_result(",
                          "pub unsafe extern \"C\" fn arch_ptrace_write_regset_body_result("]
            (out / "fixture.rs").write_text(prefix + RUST_DOUBLES + "\n".join(item(rust,s) for s in signatures) + RUST_CASES)
            xsave = registers[registers.index("struct i387_fxsave_struct {"):registers.index("typedef struct xsave_struct fp_regs_struct;")+len("typedef struct xsave_struct fp_regs_struct;")]
            c_source = "#include <stddef.h>\n" + xsave + "\n" + item(process, "struct user_regs_struct\n") + ";\n"
            c_source += C_DOUBLES + item(c,"long ptrace_read_regset(struct thread *thread, long type, struct iovec *iov)\n{")
            c_source += "\n" + item(c,"long ptrace_write_regset(struct thread *thread, long type, struct iovec *iov)\n{") + C_CASES
            (out / "fixture.c").write_text(c_source)
            self.run_checked([rustc,"--edition=2021","--test","-C","opt-level=1",str(out/"fixture.rs"),"-o",str(out/"rust-test")])
            self.run_checked([cc,"-std=gnu11","-O2","-Wall","-Wextra","-Werror",str(out/"fixture.c"),"-o",str(out/"c-test")])
            results = [subprocess.run(command,capture_output=True,text=True,timeout=30) for command in
                       ([str(out/"rust-test"),"--test-threads=1"],[str(out/"c-test")])]
            evidence = "\n".join(f"{name}: exit={result.returncode}\n{result.stdout}{result.stderr}"
                                  for name,result in zip(("Rust","C"),results))
            self.assertTrue(all(result.returncode == 0 for result in results), evidence)
            print(evidence)



if __name__ == "__main__":
    unittest.main()
