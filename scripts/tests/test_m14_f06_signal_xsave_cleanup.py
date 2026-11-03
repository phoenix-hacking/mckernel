"""Extracted production XSAVE error ownership; endpoints are observation doubles.

No actual XSAVE, usercopy, termination, native controls or full kernel is run.
Both bodies and the Rust caller's error branch are extracted verbatim.
"""
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from scripts.tests.test_m14_f06_sigreturn_transaction import item

ROOT=Path(__file__).resolve().parents[2]
C=r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
#define IHK_MC_AP_NOWAIT 2
struct thread {struct {int lock;} *sigcommon;};
static int failure,locked,freed_pending,freed_buffer,terminated;
static char pending_object;
static void *allocation;
static uint64_t get_xsave_mask(void) {return 7;}
static void *kmalloc_tracked(size_t n,int f,const char *p,int l) {(void)f;(void)p;(void)l;return allocation=failure==1?NULL:malloc(n);}
static void kfree_tracked(void *p,const char *s,int l) {
    (void)s;(void)l;
    if(p==&pending_object) {assert(locked);freed_pending++;}
    else if(p) {assert(p==allocation);free(p);allocation=NULL;freed_buffer++;}
}
static void capture(void *p) {assert(!((uintptr_t)p&63));}
static int copy_to_user(void *d,const void *s,size_t n) {(void)d;(void)s;(void)n;return failure==2?-1:0;}
void mcs_rwlock_writer_unlock(void *l,void *n) {(void)l;(void)n;assert(locked);assert(freed_pending==1);locked=0;}
static void terminate(int r,int s) {(void)r;(void)s;assert(!locked);terminated++;}
static void kprintf(const char *s) {(void)s;}
static void run(void) {
    int xsavesize=576,sig=10,mcs_rw_node=0;
    unsigned long fpregs=0x12340;
    void *pending=&pending_object;
    struct {int lock;} common={0};
    struct thread target={.sigcommon=(void *)&common},*thread=&target;
    struct {void *fpregs;} ksigsp={0};
    (void)thread;(void)mcs_rw_node;
'''
C_CASES=r'''
    assert(ksigsp.fpregs==(void *)fpregs);
out:
    if(failure) {assert(!locked);assert(freed_pending==1);assert(terminated==1);}
    else {assert(locked);assert(!freed_pending);assert(!terminated);}
    assert(allocation==NULL);
    assert(freed_buffer==(failure==1?0:1));
}
int main(void) {
    for(failure=0;failure<3;failure++) {
        locked=1;freed_pending=freed_buffer=terminated=0;allocation=NULL;run();
    }
    puts("C: allocation/copy/success XSAVE ownership cases passed");return 0;
}
'''
RUST=r'''
use abi::{CInt,CULong,SizeT,Thread,SigPending,SigCommon};
use core::{ffi::c_void,mem::{MaybeUninit,offset_of},ptr::addr_of_mut};
const IHK_MC_AP_NOWAIT:u64=2;
const ENOMEM:i32=12;
const EFAULT:i32=14;
type F06SignalSaveXstate=unsafe extern "C" fn(*mut c_void,u64);
type F06SignalCopyXstate=unsafe extern "C" fn(*mut c_void,*const c_void,usize)->i32;
static mut FAILURE:i32=0;
static mut LOCKED:bool=true;
static mut PENDING:*mut c_void=core::ptr::null_mut();
static mut ALLOCATION:*mut c_void=core::ptr::null_mut();
static mut FREED_PENDING:i32=0;
static mut FREED_BUFFER:i32=0;
static mut TERMINATED:i32=0;
mod x86_cpu_helpers {pub unsafe fn get_xsave_mask()->u64 {7}}
mod mem_helpers {
    use super::*;
    pub unsafe fn kmalloc_tracked(n:i32,_:u64,_:*mut i8,_:i32)->*mut c_void {
        if FAILURE==1 {return core::ptr::null_mut();}
        ALLOCATION=std::alloc::alloc(std::alloc::Layout::from_size_align(n as usize,8).unwrap()).cast();ALLOCATION
    }
    pub unsafe fn kfree_tracked(p:*mut c_void,_:*mut i8,_:i32) {
        if p==PENDING {assert!(LOCKED);FREED_PENDING+=1;}
        else if !p.is_null() {assert_eq!(p,ALLOCATION);std::alloc::dealloc(p.cast(),std::alloc::Layout::from_size_align(640,8).unwrap());ALLOCATION=core::ptr::null_mut();FREED_BUFFER+=1;}
    }
}
mod lock_helpers {
    pub unsafe fn __mcs_rwlock_writer_unlock(_: *mut core::ffi::c_void,_:*mut ()) {
        assert!(super::LOCKED);assert_eq!(super::FREED_PENDING,1);super::LOCKED=false;
    }
}
mod string {pub unsafe fn __inline_memset(p:*mut core::ffi::c_void,v:i32,n:usize) {core::ptr::write_bytes(p.cast::<u8>(),v as u8,n)}}
unsafe fn kprintf(_: *const i8) {}
unsafe fn f06_signal_xsave_terminate(_:i32,_:i32) {assert!(!LOCKED);TERMINATED+=1;}
unsafe fn f06_signal_dispatch_terminate(_:i32,_:i32) {assert!(!LOCKED);TERMINATED+=1;}
unsafe extern "C" fn save(p:*mut c_void,_:u64) {assert_eq!(p as usize&63,0);}
unsafe extern "C" fn copy(_: *mut c_void,_:*const c_void,_:usize)->i32 {if FAILURE==2 {-1}else{0}}
struct Node(*mut ());
impl Node {fn as_mut_ptr(&mut self)->*mut () {self.0}}
unsafe fn deliver(thread:*mut Thread,pending:*mut SigPending,signal:i32,node:*mut (),frame_fpregs:*mut *mut c_void)->i32 {
    let restart=0;
    let mut node_storage=Node(node);
    let node=&mut node_storage;
    let error=arch_do_signal_xsave_copy_body_result(576,0x12340,pending,signal,frame_fpregs,save,copy);
'''
RUST_CASES=r'''
    0
}
#[test] fn actual_xsave_ownership() {unsafe {
    for failure in 0..3 {
        FAILURE=failure;LOCKED=true;FREED_PENDING=0;FREED_BUFFER=0;TERMINATED=0;
        let mut thread=MaybeUninit::<Thread>::zeroed();
        let mut common=MaybeUninit::<abi::SigCommon>::zeroed();
        (*thread.as_mut_ptr()).sigcommon=common.as_mut_ptr().cast();
        let mut pending=MaybeUninit::<SigPending>::zeroed();PENDING=pending.as_mut_ptr().cast();
        let mut fp=core::ptr::null_mut();
        deliver(thread.as_mut_ptr(),pending.as_mut_ptr(),10,core::ptr::null_mut(),&mut fp);
        assert!(ALLOCATION.is_null());
        assert_eq!(FREED_BUFFER,if failure==1 {0}else{1});
        if failure!=0 {assert!(!LOCKED);assert_eq!(FREED_PENDING,1);assert_eq!(TERMINATED,1);}
        else {assert!(LOCKED);assert_eq!(FREED_PENDING,0);assert_eq!(TERMINATED,0);assert_eq!(fp as usize,0x12340);}
    }
}}
'''

class F06SignalXsaveCleanupTests(unittest.TestCase):
    def checked(self,args):
        r=subprocess.run(args,capture_output=True,text=True,timeout=60)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        return r

    def test_c_xsave_error_ownership(self):
        cc=os.environ.get('CC') or shutil.which('gcc')
        if cc is None:
            self.skipTest('GCC required for the isolated fixture')
        source=(ROOT/'arch/x86_64/kernel/syscall.c').read_text()
        signal=item(source,'int\ndo_signal(')
        body=item(signal,'if(xsavesize){')
        instruction='asm volatile("xsave %0" : : "m"(*kfpregs), "a"(low), "d"(high) : "memory");'
        self.assertIn(instruction,body)
        body=body.replace(instruction,'capture(kfpregs); (void)low; (void)high;')
        with tempfile.TemporaryDirectory(prefix='m14-f06-xsave-c-') as tmp:
            path=Path(tmp);(path/'test.c').write_text(C+body+C_CASES)
            self.checked([cc,'-std=gnu11','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(path/'test.c'),'-o',str(path/'test')])
            print(self.checked([str(path/'test')]).stdout)

    def test_rust_xsave_error_ownership(self):
        rustc=os.environ.get('RUSTC') or shutil.which('rustc')
        if rustc is None:
            self.skipTest('rustc required for the isolated fixture')
        source=(ROOT/'kernel/rust/f06_signal_tail.rs').read_text()
        body=item(source,'pub unsafe extern "C" fn arch_do_signal_xsave_copy_body_result(')
        signal=item(source,'pub unsafe extern "C" fn do_signal(')
        tail=signal[signal.index('arch_do_signal_xsave_copy_result('):]
        error=item(tail,'if error != 0 {')
        with tempfile.TemporaryDirectory(prefix='m14-f06-xsave-rs-') as tmp:
            path=Path(tmp)
            prefix='#![allow(dead_code,unused_imports,unused_variables,static_mut_refs)]\n'
            prefix+=f'#[path={json.dumps(str(ROOT/"kernel/rust/abi.rs"))}] mod abi;\n'
            from scripts.derive_f06_signal_metadata import derive_signal_metadata
            origin = '/src/arch/x86_64/kernel/syscall.c'
            fields = derive_signal_metadata((ROOT/'arch/x86_64/kernel/syscall.c').read_text(), origin)
            prefix += f'const F06_SIGNAL_ORIGIN: &[u8] = b"{origin}\\0";\n'
            for name, value in fields.items():
                kind = 'u32' if name.endswith('FLAGS') else 'i32'
                prefix += f'const {name}: {kind} = {value};\n'
            (path/'test.rs').write_text(prefix+RUST+error+RUST_CASES+body)
            self.checked([rustc,'--edition=2021','--test',str(path/'test.rs'),'-o',str(path/'test')])
            print(self.checked([str(path/'test'),'--test-threads=1']).stdout)

if __name__=='__main__':unittest.main()
