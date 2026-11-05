"""Observe balanced writer ownership around the genuine munmap helper."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.tests.test_m14_f06_tail_codegen import definition

ROOT = Path(__file__).resolve().parents[2]
RUST_OBSERVER = r'''

use std::sync::Mutex;
use core::sync::atomic::{AtomicPtr,Ordering};
#[derive(Debug,Default)]
struct Observation { depth:i32, unbalanced:bool, unprotected:bool, mapping_present:bool,
    trace:Vec<char>, logs:Vec<(i32,i32,u64,usize,i32)>, args:Option<(u64,usize,i32)>, result:i32 }
static RUN:Mutex<()>=Mutex::new(());
static ACTIVE:AtomicPtr<Observation>=AtomicPtr::new(core::ptr::null_mut());
unsafe extern "C" fn lock(ptr:*mut c_void){
    let s=&mut*ACTIVE.load(Ordering::SeqCst);
    if ptr!=s as *mut _ as *mut c_void{s.unbalanced=true;}
    s.trace.push('L');s.depth+=1;
}
unsafe extern "C" fn unlock(ptr:*mut c_void){
    let s=&mut*ACTIVE.load(Ordering::SeqCst);
    if ptr!=s as *mut _ as *mut c_void{s.unbalanced=true;}
    s.trace.push('U');if s.depth==0{s.unbalanced=true;}else{s.depth-=1;}
}
unsafe extern "C" fn mutate(addr:*mut c_void,len:SizeT,holding:CInt)->CInt{
    let s=&mut*ACTIVE.load(Ordering::SeqCst);s.trace.push('M');
    s.unprotected|=s.depth!=1||holding!=1;s.mapping_present=false;
    s.args=Some((addr as CULong,len,holding));s.result
}
unsafe extern "C" fn log(event:CInt,cpu:CInt,addr:CULong,len:SizeT,result:CInt){
    let s=&mut*ACTIVE.load(Ordering::SeqCst);s.logs.push((event,cpu,addr,len,result));
}
fn run(mask:u8,addr:CULong,len:SizeT,mutator_result:CInt,expected:CInt,mutated:bool){
    let _guard=RUN.lock().unwrap_or_else(|e|e.into_inner());
    let mut s=Observation{mapping_present:true,result:mutator_result,..Default::default()};
    ACTIVE.store(&mut s,Ordering::SeqCst);
    let rc=unsafe{munmap_body_result(core::ptr::null_mut(),(&mut s as *mut Observation).cast(),addr,len,
        0x1000,0x100000,6,
        if mask&1!=0{Some(lock)}else{None},if mask&2!=0{Some(unlock)}else{None},
        if mask&4!=0{Some(mutate)}else{None},Some(log))};
    ACTIVE.store(core::ptr::null_mut(),Ordering::SeqCst);
    eprintln!("mask={mask} rc={rc} observation={s:?}");
    assert_eq!(rc,expected,"return mask={mask}");
    assert_eq!(s.mapping_present,!mutated,"mapping changed mask={mask}");
    assert_eq!(s.depth,0,"unreleased writer mask={mask}");
    assert!(!s.unbalanced,"unlock without matching acquisition mask={mask}");
    assert!(!s.unprotected,"mutator ran without writer mask={mask}");
    assert_eq!(s.trace,if mutated{vec!['L','M','U']}else{vec![]},"provider trace mask={mask}");
    let mut expected_logs=vec![(1,6,addr,len,0),(2,6,addr,len,expected)];
    if cfg!(enable_fugaku_hacks)&&expected!=0{expected_logs.push((3,6,addr,len,expected));}
    assert_eq!(s.logs,expected_logs);
    if mutated{assert_eq!(s.args,Some((addr,0x2000,1)));}else{assert_eq!(s.args,None);}
}
macro_rules! missing {($name:ident,$mask:expr)=>{#[test] fn $name(){run($mask,0x4000,0x1001,0,-22,false);}};}
missing!(all_required_providers_absent,0);
missing!(missing_unlock_and_mutator,1);
missing!(unlock_without_lock,2);
missing!(mutator_absent_before_acquire,3);
missing!(mutator_without_writer_pair,4);
missing!(missing_unlock_must_not_mutate_or_acquire,5);
missing!(missing_lock_must_not_mutate_or_unlock,6);
#[test] fn ordinary_success_keeps_exact_order_and_rounding(){run(7,0x4000,0x1001,0,0,true);}
#[test] fn ordinary_mutator_error_unlocks_once_and_preserves_error(){run(7,0x4000,0x1001,-12,-12,true);}
#[test] fn invalid_unaligned_range_has_no_side_effects(){for mask in 0..8{run(mask,0x4001,0x1001,0,-22,false);}}
#[test] fn zero_length_rejected_before_acquisition(){for mask in 0..8{run(mask,0x4000,0,0,-22,false);}}
#[test] fn overflow_length_rejected_before_acquisition(){for mask in 0..8{run(mask,0x4000,usize::MAX,0,-22,false);}}
'''


def build_fixture(directory, source=None):
    policy = source if source is not None else (ROOT / "kernel/rust/syscall_policy.rs").read_text()
    pieces = ["#![allow(dead_code,unsafe_op_in_unsafe_fn)]",
              f'#[path="{ROOT / "kernel/rust/abi.rs"}"] mod abi;',
              "use abi::{CInt,CULong,SizeT}; use core::ffi::c_void; use core::ptr::write;"]
    for name in ("EINVAL", "PAGE_SIZE", "PAGE_MASK", "MUNMAP_LOG_ENTER", "MUNMAP_LOG_EXIT", "MUNMAP_LOG_ERROR"):
        pieces.append(re.search(r"(?m)^const " + name + r"\s*:[^;]+;", policy).group())
    for name in ("SyscallRwlockFn", "MunmapDoFn", "MunmapLogFn"):
        pieces.append(re.search(r"(?m)^type " + name + r"\s*=[^;]+;", policy).group())
    for name in ("munmap_prepare_range", "munmap_body_result"):
        pieces.append(definition(policy, name))
    pieces.append(RUST_OBSERVER)
    fixture = directory / "munmap_writer.rs"
    fixture.write_text("\n\n".join(pieces) + "\n")
    return fixture


class MunmapWriterTests(unittest.TestCase):
    def test_required_writer_transaction_and_original_range_contract(self):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        if not compiler:
            self.skipTest("Rust compiler required")
        with tempfile.TemporaryDirectory(prefix="m14-munmap-writer-") as tmp:
            directory = Path(tmp)
            fixture = build_fixture(directory)
            binary = directory / "munmap_writer"
            compiled = subprocess.run([compiler, "--edition=2021", "--test", "-C", "opt-level=0",
                                       "-C", "codegen-units=1", str(fixture), "-o", str(binary)],
                                      capture_output=True, text=True, timeout=45)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            result = subprocess.run([str(binary), "--test-threads=1"],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("12 passed; 0 failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
