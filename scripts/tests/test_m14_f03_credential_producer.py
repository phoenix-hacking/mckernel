"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Extract exact affected bodies and producer for bounded callback observations.
No compiler or test is executed by this script.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
import re

REPO = Path(__file__).resolve().parents[2]


def definition(source, name, kind='fn'):
    pattern = (r'^(?:pub(?:\([^)]*\))? )?(?:unsafe )?(?:extern "C" )?'
               + kind + ' ' + re.escape(name) + r'\b')
    match = re.search(pattern, source, re.M)
    if match is None:
        raise ValueError('missing exact definition: ' + name)
    opening = source.index('{', match.start())
    end, depth = opening + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end]


def build_fixture(directory):
    guest = (REPO/'kernel/rust/syscall_policy.rs').read_text()
    host = (REPO/'executer/user/rust/mcexec_helpers.rs').read_text()
    platform = (REPO/'executer/user/rust/mcexec_platform_syscalls.rs').read_text()
    producer = (REPO/'executer/kernel/mcctrl/rust/mcctrl_helpers.rs').read_text()
    abi = (REPO/'kernel/rust/abi.rs').read_text()
    pieces = ['use core::ffi::{c_int,c_long,c_uint,c_ulong,c_void};',
              'use core::mem::{MaybeUninit,offset_of};',
              'use core::ptr::{null_mut,write};']
    for name in ('CInt','CLong','CULong','SizeT'):
        pieces.append(re.search(r'^pub type '+name+r' = [^;]+;',abi,re.M).group())
    pieces.append('#[repr(C)]\n'+definition(abi,'SyscallRequest','struct'))
    for name in ('McexecSyscallRequest','McexecSyscallWaitDesc'):
        pieces.append('#[repr(C)]\n'+definition(host,name,'struct'))
    for source,names in [(guest,('SyscallVirtToPhysFn','SyscallGetCpuFn','SyscallRequestCallFn','SyscallGetcredFn')),
                         (producer,('McctrlControlPhysToVirtFn','McctrlControlCredValueFn'))]:
        for name in names:
            pieces.append(re.search(r'^(?:pub )?type '+name+r'\s*= [^;]+;',source,re.M).group())
    for name in ('EINVAL','EFAULT'):
        pieces.append(re.search(r'^const '+name+r': CInt = [^;]+;',guest,re.M).group())
    for name in ('getcred_body_result','syscall_refresh_cred_fields_body_result'):
        pieces.append(definition(guest,name))
    for name in ('mcexec_errno_return_result','mcexec_setfsuid_needs_cred_result','act_setfsuid'):
        pieces.append(definition(host,name))
    for name in ('mcctrl_control_fill_cred_values','mcctrl_control_getcred_body_result'):
        pieces.append(definition(producer,name))
    bridge_body=definition(platform,'mcexec_cred_get_bridge')
    converted=definition(platform,'converted')
    pieces.append('mod platform { use super::{c_int,c_long,c_ulong};\n'+converted+'\n'+bridge_body+'\n}')
    pieces.append('use platform::mcexec_cred_get_bridge;')
    pieces.append('''mod real_bridge {
      use core::ffi::{c_int,c_long,c_ulong};
      unsafe extern "C" {fn ioctl(fd:c_int,request:c_ulong,...)->c_int;
        fn __errno_location()->*mut c_int;}
      use super::mcexec_errno_return_result;
      pub mod platform {use super::{c_int,c_long,c_ulong};
    '''+converted+'\n'+bridge_body+'\n}}')
    pieces.append(RUST_OBSERVER)
    output = directory / "credential_provider.rs"
    output.write_text("\n\n".join(pieces) + "\n")
    return output


RUST_OBSERVER = r'''
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Callback observations only; no fake runtime ownership or completion provider.
use std::sync::{Mutex,atomic::{AtomicI32,AtomicI64,AtomicUsize,Ordering}};
static SERIAL:Mutex<()>=Mutex::new(());
static MODE:AtomicI32=AtomicI32::new(0); // 0 real extracted producer, 1 failed ioctl, 2 partial then error
static PREFIX:AtomicUsize=AtomicUsize::new(0);
static RET:AtomicI64=AtomicI64::new(0);
static RETURNS:AtomicUsize=AtomicUsize::new(0);
static IOCTLS:AtomicUsize=AtomicUsize::new(0);
static FSIDS:AtomicUsize=AtomicUsize::new(0);
static BAD_REQUEST:AtomicI32=AtomicI32::new(0);
static mut OBSERVED_ERRNO:i32=0;
const IDS:[i32;8]=[101,102,103,104,201,202,203,204];
unsafe fn __errno_location()->*mut i32 {core::ptr::addr_of_mut!(OBSERVED_ERRNO)}
unsafe extern "C" fn mapped(physical:c_ulong)->c_ulong {physical}
unsafe extern "C" fn uid()->c_int {IDS[0]}
unsafe extern "C" fn euid()->c_int {IDS[1]}
unsafe extern "C" fn suid()->c_int {IDS[2]}
unsafe extern "C" fn fsuid()->c_int {IDS[3]}
unsafe extern "C" fn gid()->c_int {IDS[4]}
unsafe extern "C" fn egid()->c_int {IDS[5]}
unsafe extern "C" fn sgid()->c_int {IDS[6]}
unsafe extern "C" fn fsgid()->c_int {IDS[7]}
unsafe fn ioctl(_:c_int,request:c_ulong,arg:c_ulong)->c_int {
    IOCTLS.fetch_add(1,Ordering::SeqCst);
    if request!=0x30a0290a {BAD_REQUEST.store(1,Ordering::SeqCst);}
    if MODE.load(Ordering::SeqCst)==0 {
        unsafe {mcctrl_control_getcred_body_result(arg,Some(mapped),Some(uid),Some(euid),Some(suid),
            Some(fsuid),Some(gid),Some(egid),Some(sgid),Some(fsgid))}
    } else {
        // A bounded observer models a stopped partial store followed by an
        // actual errno. It does not claim native mcctrl fault injection.
        if MODE.load(Ordering::SeqCst)==2 {
            for index in 0..PREFIX.load(Ordering::SeqCst) {
                unsafe {(arg as *mut i32).add(index).write(IDS[index])};
            }
        }
        unsafe {OBSERVED_ERRNO=if MODE.load(Ordering::SeqCst)==1 {13} else {14}};
        -1
    }
}
unsafe extern "C" fn do_syscall_return(_:c_int,_:c_int,ret:c_long,_:c_int,_:c_ulong,_:c_ulong,_:c_ulong) {
    RETURNS.fetch_add(1,Ordering::SeqCst);RET.store(ret,Ordering::SeqCst);
}
unsafe extern "C" fn mcexec_cred_setfsuid_bridge(_:c_ulong)->c_long {
    FSIDS.fetch_add(1,Ordering::SeqCst);1234
}
unsafe extern "C" fn virtual_to_physical(ptr:*mut c_void)->CULong {ptr as CULong}
unsafe extern "C" fn cpu()->CInt {3}
unsafe extern "C" fn offload(request:*mut SyscallRequest,processor:CInt)->CLong {
    let r=unsafe{&*request};
    if processor!=3||r.number!=122||r.rtid!=0||r.ttid!=0||r.valid!=0||r.args[1]!=1||r.args[2..]!=[0;4] {
        BAD_REQUEST.store(1,Ordering::SeqCst);
    }
    // Observe selected scratch initialization before handing the existing
    // by-address request to the exact extracted host action and bridge.
    for index in 0..8 {
        if unsafe{*(r.args[0] as *const i32).add(index)}!=0 {BAD_REQUEST.store(1,Ordering::SeqCst);}
    }
    let wait=McexecSyscallWaitDesc{cpu:processor as c_ulong,
        sr:McexecSyscallRequest{rtid:r.rtid,ttid:r.ttid,valid:r.valid,number:r.number,args:r.args},pid:1};
    unsafe{act_setfsuid(&wait,7,processor)};
    RET.load(Ordering::SeqCst)
}
unsafe extern "C" fn snapshot(scratch:*mut CInt)->*mut CInt {
    unsafe{getcred_body_result(scratch,(!4095_u64),122,Some(virtual_to_physical),Some(cpu),Some(offload))}
}
#[repr(C)] struct Cache{ids:[i32;8]}
#[repr(C)] struct Current{proc:*mut Cache}
fn reset(mode:i32,prefix:usize){
    MODE.store(mode,Ordering::SeqCst);PREFIX.store(prefix,Ordering::SeqCst);
    RET.store(999,Ordering::SeqCst);RETURNS.store(0,Ordering::SeqCst);
    IOCTLS.store(0,Ordering::SeqCst);FSIDS.store(0,Ordering::SeqCst);BAD_REQUEST.store(0,Ordering::SeqCst);
}
unsafe fn refresh_group(group:usize,scratch:*mut i32,cache:*mut Cache)->i32 {
    let mut current=Current{proc:cache};
    let base=core::mem::offset_of!(Cache,ids)+group*core::mem::size_of::<i32>();
    unsafe{syscall_refresh_cred_fields_body_result((&mut current as *mut Current).cast(),scratch,
        offset_of!(Current,proc),base,base+4,base+8,base+12,group,group+1,group+2,group+3,Some(snapshot))}
}
#[test] fn real_libc_invalid_descriptor_preserves_actual_ebadf(){
    assert_eq!(unsafe{real_bridge::platform::mcexec_cred_get_bridge(-1,0)},-9);
}
#[test] fn success_real_extracted_producer_publishes_exact_uid_gid(){
    let _guard=SERIAL.lock().unwrap_or_else(|e|e.into_inner());
    for group in [0,4] {
        reset(0,0);let mut scratch=[-777;16];let mut cache=Cache{ids:[9;8]};
        assert_eq!(unsafe{refresh_group(group,scratch.as_mut_ptr(),&mut cache)},0);
        let mut expected=[9;8];expected[group..group+4].copy_from_slice(&IDS[group..group+4]);
        assert_eq!(cache.ids,expected);assert_eq!(RET.load(Ordering::SeqCst),0);
        assert_eq!(RETURNS.load(Ordering::SeqCst),1);assert_eq!(BAD_REQUEST.load(Ordering::SeqCst),0);
    }
}
#[test] fn failed_or_partial_ioctl_never_publishes_credential_fields(){
    let _guard=SERIAL.lock().unwrap_or_else(|e|e.into_inner());
    for (mode,prefix) in [(1,0)].into_iter().chain((0..8).map(|n|(2,n))) {
        for group in [0,4] {
            reset(mode,prefix);let mut scratch=[-777;16];let mut cache=Cache{ids:[9;8]};
            assert_eq!(unsafe{refresh_group(group,scratch.as_mut_ptr(),&mut cache)},-14);
            assert_eq!(cache.ids,[9;8]);
            assert_eq!(RET.load(Ordering::SeqCst),if mode==1{-13}else{-14});
            assert_eq!(RETURNS.load(Ordering::SeqCst),1);assert_eq!(BAD_REQUEST.load(Ordering::SeqCst),0);
        }
    }
}
#[test] fn ordinary_setfsuid_keeps_previous_id_contract(){
    let _guard=SERIAL.lock().unwrap_or_else(|e|e.into_inner());reset(0,0);
    let w=McexecSyscallWaitDesc{cpu:3,sr:McexecSyscallRequest{rtid:0,ttid:0,valid:0,number:122,args:[2000,0,0,0,0,0]},pid:1};
    unsafe{act_setfsuid(&w,7,3)};
    assert_eq!(RET.load(Ordering::SeqCst),1234);assert_eq!(IOCTLS.load(Ordering::SeqCst),0);
    assert_eq!(FSIDS.load(Ordering::SeqCst),1);
}
#[test] fn positive_nonzero_offload_is_not_a_snapshot(){
    unsafe extern "C" fn positive(_: *mut SyscallRequest,_:CInt)->CLong{7}
    let mut scratch=[-777;16];
    assert!(unsafe{getcred_body_result(scratch.as_mut_ptr(),!4095_u64,122,
        Some(virtual_to_physical),Some(cpu),Some(positive))}.is_null());
    assert_eq!(scratch,[0;16]);
}

const _: () = {
    assert!(core::mem::size_of::<[CInt;8]>()==32);
    assert!(core::mem::size_of::<SyscallRequest>()==72);
    assert!(core::mem::size_of::<McexecSyscallRequest>()==72);
    assert!(offset_of!(SyscallRequest,args)==24);
    assert!(offset_of!(McexecSyscallRequest,args)==24);
    assert!(offset_of!(McexecSyscallWaitDesc,sr)==8);
};
'''


class CredentialProducerTests(unittest.TestCase):
    def test_opt_in_c_refresh_entries_have_one_selected_owner(self):
        compiler = os.environ.get("CC") or shutil.which("gcc")
        if not compiler:
            self.skipTest("C preprocessor required")
        source = (REPO / "kernel/syscall.c").read_text()
        marker = ("#if defined(MCKERNEL_RUST_F03_FORWARD_ADAPTERS) && "
                  "defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS)\n"
                  "extern void do_setresuid(void);")
        start = source.index(marker)
        end = source.index("\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n"
                           "long sys_setresuid", start)
        region = source[start:end]
        for adapters, helpers in ((False, False), (False, True),
                                  (True, False), (True, True)):
            with self.subTest(adapters=adapters, helpers=helpers):
                command = [compiler, "-E", "-P", "-x", "c", "-"]
                if adapters:
                    command.append("-DMCKERNEL_RUST_F03_FORWARD_ADAPTERS=1")
                if helpers:
                    command.append("-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS=1")
                result = subprocess.run(command, input=region, capture_output=True,
                                        text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                for name in ("do_setresuid", "do_setresgid"):
                    definitions = re.findall(r"\bvoid\s+" + name
                                             + r"\s*\([^;{}]*\)\s*\{", result.stdout)
                    self.assertEqual(len(definitions), 0 if adapters and helpers else 1)
                    if adapters and helpers:
                        self.assertIn("extern void " + name + "(void);", result.stdout)

    def test_real_ioctl_errors_and_genuine_snapshot_publication(self):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        if not compiler:
            self.skipTest("Rust compiler required")
        with tempfile.TemporaryDirectory(prefix="m14-credential-producer-") as tmp:
            directory = Path(tmp)
            source = build_fixture(directory)
            binary = directory / "credential_provider"
            result = subprocess.run([compiler, "--edition=2021", "--test", "-C", "opt-level=1",
                                     str(source), "-o", str(binary)],
                                    capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary), "--test-threads=1"],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("5 passed; 0 failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
