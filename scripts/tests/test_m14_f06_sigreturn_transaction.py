"""Focused production-source signal-return/restart regressions.

Actual C/Rust bodies execute with explicit allocation/usercopy/syscall/FP
observation doubles. GS context lookup and inline XRSTOR in the extracted C body
are the only replaced instruction endpoints. No kernel crate, privileged/native
execution or production provider acceptance is claimed.
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
    opening = source.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


RUST = r'''
use abi::{CInt, CLong, CULong, SizeT, SigStack, SigInfo, X86UserContext};
use core::{ffi::c_void, mem::{size_of, offset_of, MaybeUninit}, ptr::{write_volatile,read_volatile}};
const EFAULT: i32 = 14;
const ENOMEM: i32 = 12;
const RFLAGS_TF: u64 = 256;
const TRAP_TRACE: i32 = 2;
const SIGTRAP: i32 = 5;
type SyscallCopyFromUserFn = unsafe extern "C" fn(*mut u8,u64,usize)->i64;
type SyscallForwardContextFn = unsafe extern "C" fn(i32,*mut c_void)->i64;
type ArchRtSigreturnSetSignalFn = unsafe extern "C" fn(i32,*mut c_void,*const SigInfo);
type PtraceVoidFn = unsafe extern "C" fn();
type ArchRtSigreturnCheckSignalFn = unsafe extern "C" fn(i32,*mut c_void,i32);
type ArchPtraceAllocFn = unsafe extern "C" fn(usize,u64)->*mut c_void;
type ArchRtSigreturnFreeFn = unsafe extern "C" fn(*mut c_void);
type ArchRtSigreturnXrstorFn = unsafe extern "C" fn(*mut c_void);
fn register_snapshot(regs:&X86UserContext)->([u64;21],[u64;6],[u8;8]) {
    let g=&regs.gpr;let sr=&regs.sr;
    ([g.r15,g.r14,g.r13,g.r12,g.rbp,g.rbx,g.r11,g.r10,g.r9,g.r8,g.rax,
      g.rcx,g.rdx,g.rsi,g.rdi,g.orig_rax,g.rip,g.cs,g.rflags,g.rsp,g.ss],
     [sr.fs_base,sr.gs_base,sr.ds,sr.es,sr.fs,sr.gs],
     [regs.is_gpr_valid,regs.is_sr_valid,regs.spare_flags6,regs.spare_flags5,
      regs.spare_flags4,regs.spare_flags3,regs.spare_flags2,regs.spare_flags1])
}
fn stack_snapshot(stack:&SigStack)->(usize,i32,i32,usize) {
    (stack.ss_sp as usize,stack.ss_flags,stack.padding,stack.ss_size)
}
#[repr(C)] struct Target {mask:u64, stack:SigStack}
static mut FRAME: *mut RtSigreturnFrame = core::ptr::null_mut();
static mut FAILURE:i32=0;
static mut MUTATE:bool=false;
static mut EVENTS:Vec<i32>=Vec::new();
static mut ALLOCATION:*mut c_void=core::ptr::null_mut();
unsafe extern "C" fn copy(dst:*mut u8,src:u64,n:usize)->i64 {
    if src==FRAME as u64 {
        core::ptr::copy_nonoverlapping(src as *const u8,dst,n);
        EVENTS.push(1);
        if MUTATE {(*FRAME).restart=0;(*FRAME).num=999;(*FRAME).sigrc=777;}
        0
    } else {EVENTS.push(3);if FAILURE==2 {-1} else {core::ptr::write_bytes(dst,0,n);0}}
}
unsafe extern "C" fn alloc(n:usize,_:u64)->*mut c_void {
    EVENTS.push(2);
    if FAILURE==1 {return core::ptr::null_mut();}
    ALLOCATION=std::alloc::alloc(std::alloc::Layout::from_size_align(n,8).unwrap()).cast();
    ALLOCATION
}
unsafe extern "C" fn free(p:*mut c_void) {
    assert_eq!(p,ALLOCATION);
    EVENTS.push(5);
    std::alloc::dealloc(p.cast(),std::alloc::Layout::from_size_align(640,8).unwrap());
    ALLOCATION=core::ptr::null_mut();
}
unsafe extern "C" fn restore(p:*mut c_void) {assert_eq!(p as usize&63,0);EVENTS.push(4);}
unsafe extern "C" fn syscall(n:i32,_:*mut c_void)->i64 {assert_eq!(n,7);EVENTS.push(6);123}
unsafe extern "C" fn signal(_:i32,_:*mut c_void,_:*const SigInfo) {EVENTS.push(7);}
unsafe extern "C" fn resched() {EVENTS.push(8);}
unsafe extern "C" fn check(_:i32,_:*mut c_void,_:i32) {EVENTS.push(9);}
#[test] fn actual_sigreturn_transaction() {unsafe {
    for mode in 0..7 {
        let mut frame:RtSigreturnFrame=core::mem::zeroed();
        let mut regs:X86UserContext=core::mem::zeroed();
        let mut target:Target=core::mem::zeroed();
        FRAME=&mut frame;FAILURE=0;MUTATE=false;EVENTS.clear();
        frame.sigrc=42;frame.num=7;
        frame.regs[RTSIG_REG_R15]=0xaaaa;
        frame.regs[RTSIG_REG_OLDMASK]=0x5555;
        target.mask=0x2222;target.stack.ss_sp=0x4000 as *mut c_void;target.stack.ss_size=8192;
        regs.gpr.r15=0xbbbb;regs.gpr.rax=0xcccc;regs.gpr.rflags=0x202;
        frame.regs[RTSIG_REG_RSP]=0x1230;
        regs.gpr.rsp=FRAME as u64;
        let old_regs=register_snapshot(&regs);
        let old_target=(target.mask,stack_snapshot(&target.stack));
        if mode!=0 && mode!=1 {frame.fpregs=0x12340 as *mut c_void;}
        if mode==1 || mode==5 {MUTATE=true;}
        if mode==2 {FAILURE=1;}
        if mode==3 {FAILURE=2;}
        if mode==4 || mode==5 {frame.restart=1;}
        if mode==6 {frame.regs[RTSIG_REG_RFLAGS]=RFLAGS_TF;}
        let result=arch_rt_sigreturn_body_result((&mut target as *mut Target).cast(),&mut regs,
            offset_of!(Target,mask),offset_of!(Target,stack),size_of::<SigStack>(),
            size_of::<RtSigreturnFrame>(),576,2,Some(copy),Some(syscall),Some(signal),
            Some(resched),Some(check),Some(alloc),Some(free),Some(restore));
        let (expected,events):(i64,&[i32])=match mode {
            0|1=>(42,&[1]),2=>(-12,&[1,2]),3=>(-14,&[1,2,3,5]),
            4|5=>(123,&[1,2,3,4,5,6]),6=>(42,&[1,2,3,4,5,7,8,9]),_=>unreachable!()};
        assert_eq!(result,expected,"mode={mode}");
        if mode==2 || mode==3 {
            assert_eq!(register_snapshot(&regs),old_regs);
            assert_eq!((target.mask,stack_snapshot(&target.stack)),old_target);
        } else {assert_eq!(regs.gpr.r15,0xaaaa);assert_eq!(target.mask,0x5555);}
        assert_eq!(&*core::ptr::addr_of!(EVENTS),events,"mode={mode}");
        assert!(ALLOCATION.is_null(),"mode={mode}");
    }
}}
'''
NATIVE = r'''
static mut NATIVE_ERROR:i64=0;
unsafe extern "C" fn native_copy(dst:*mut u8,src:u64,n:usize)->i64 {
    core::ptr::copy_nonoverlapping(src as *const u8,dst,n);0
}
unsafe extern "C" fn native_fp(_:u64,_:i32)->i64 {NATIVE_ERROR}
#[test] fn actual_native_sigreturn_keeps_state_on_fp_failure() {unsafe {
    for error in [0,-12,-14] {
        NATIVE_ERROR=error;
        let mut vm:abi::ProcessVm=core::mem::zeroed();vm.region.user_start=0x1000;vm.region.user_end=1<<47;
        let mut thread:abi::Thread=core::mem::zeroed();thread.vm=&mut vm;
        thread.sigmask.val[0]=0x2222;thread.sigstack.ss_sp=0x20000 as *mut c_void;thread.sigstack.ss_size=8192;
        let mut regs:X86UserContext=core::mem::zeroed();regs.gpr.r15=0xbbbb;regs.gpr.rax=15;regs.gpr.rflags=0x202;
        let mut frame:native_signal::Frame=core::mem::zeroed();frame.regs[7]=0xaaaa;frame.regs[13]=42;
        frame.regs[15]=0x70000;frame.regs[16]=0x50000;frame.sigmask[0]=0x5555;
        regs.gpr.rsp=(&frame as *const native_signal::Frame) as u64;
        let old_regs=register_snapshot(&regs);
        let old_thread=(thread.sigmask.val,stack_snapshot(&thread.sigstack));
        let result=native_signal::sigreturn(&mut thread,&mut regs,576,native_copy,native_fp);
        if error!=0 {
            assert_eq!(result,Err(error));
            assert_eq!(register_snapshot(&regs),old_regs);
            assert_eq!((thread.sigmask.val,stack_snapshot(&thread.sigstack)),old_thread);
        } else {assert_eq!(result,Ok(42));assert_eq!(regs.gpr.r15,0xaaaa);assert_eq!(thread.sigmask.val[0],0x5555&!((1<<8)|(1<<18)));}
    }
}}
'''

C = r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <stddef.h>
#define RFLAGS_TF 256
#define TRAP_TRACE 2
#define SIGTRAP 5
#define IHK_MC_AP_NOWAIT 2
struct siginfo {int si_code;};
typedef struct siginfo siginfo_t;
typedef struct {void *ss_sp;int ss_flags;size_t ss_size;} stack_t;
struct x86_user_context {struct {unsigned long r15,r14,r13,r12,rbp,rbx,r11,r10,r9,r8,rax,rcx,rdx,rsi,rdi,error,rip,rflags,rsp;} gpr;};
typedef struct x86_user_context ihk_mc_user_context_t;
struct thread {struct {unsigned long __val[1];} sigmask;stack_t sigstack;};
struct cpu {struct thread *current;} cpu;
static struct cpu *get_this_cpu_local_var(void) {return &cpu;}
static struct x86_user_context *fixture_regs;
static struct sigsp *fixture_frame;
static int failure,mutate,events[16],event_count;
static void *allocation;
static void event(int n) {events[event_count++]=n;}
static int get_xsave_size(void) {return 576;}
static uint64_t get_xsave_mask(void) {return 7;}
static void *kmalloc_tracked(size_t n,unsigned long f,const char *file,int line) {
    (void)f;(void)file;(void)line;event(2);return allocation=failure==1?NULL:malloc(n);
}
static void kfree_tracked(void *p,const char *file,int line) {(void)file;(void)line;assert(p==allocation);event(5);free(p);allocation=NULL;}
static void fixture_restore(void *p) {assert(((uintptr_t)p&63)==0);event(4);}
static long syscall(int n,ihk_mc_user_context_t *r) {(void)r;assert(n==7);event(6);return 123;}
static void set_signal(int sig,void *r,void *i) {(void)sig;(void)r;(void)i;event(7);}
static void check_need_resched(void) {event(8);}
static void check_signal(int s,void *r,int n) {(void)s;(void)r;(void)n;event(9);}
'''
C_CASES = r'''
static int copy_from_user(void *dst,const void *src,size_t n) {
    if (src==fixture_frame) {
        memcpy(dst,src,n);event(1);
        if (mutate) {fixture_frame->restart=0;fixture_frame->num=999;fixture_frame->sigrc=777;}
        return 0;
    }
    event(3);if (failure==2) return -1;memset(dst,0,n);return 0;
}
int main(void) {
    for (int mode=0;mode<7;mode++) {
        struct sigsp frame={0};struct x86_user_context regs={0};struct thread thread={0};
        fixture_frame=&frame;fixture_regs=&regs;cpu.current=&thread;
        failure=0;mutate=0;event_count=0;allocation=NULL;
        frame.sigrc=42;frame.num=7;frame._rsp=0x1230;frame._r15=0xaaaa;frame._oldmask=0x5555;
        regs.gpr.rsp=(uintptr_t)&frame;regs.gpr.r15=0xbbbb;regs.gpr.rax=0xcccc;regs.gpr.rflags=0x202;
        thread.sigmask.__val[0]=0x2222;thread.sigstack.ss_sp=(void *)0x4000;thread.sigstack.ss_size=8192;
        struct x86_user_context old_regs;memcpy(&old_regs,&regs,sizeof regs);
        struct thread old_thread;memcpy(&old_thread,&thread,sizeof thread);
        if (mode!=0 && mode!=1) frame.fpregs=(void *)0x12340;
        if (mode==1 || mode==5) mutate=1;
        if (mode==2) failure=1;
        if (mode==3) failure=2;
        if (mode==4 || mode==5) frame.restart=1;
        if (mode==6) frame._rflags=RFLAGS_TF;
        long result=sys_rt_sigreturn(0,&regs);
        long expected=mode==2?-12:mode==3?-14:(mode==4||mode==5)?123:42;
        if (result!=expected) {fprintf(stderr,"C mode=%d result=%ld expected=%ld\n",mode,result,expected);return 1;}
        if(mode==2 || mode==3) {assert(!memcmp(&regs,&old_regs,sizeof regs));assert(!memcmp(&thread,&old_thread,sizeof thread));}
        else {assert(regs.gpr.r15==0xaaaa);assert(thread.sigmask.__val[0]==0x5555);}
        const int ordinary[]={1},oom[]={1,2},fault[]={1,2,3,5},restart[]={1,2,3,4,5,6},trace[]={1,2,3,4,5,7,8,9};
        const int *want=mode<2?ordinary:mode==2?oom:mode==3?fault:mode<6?restart:trace;
        int count=mode<2?1:mode==2?2:mode==3?4:mode<6?6:8;
        assert(event_count==count && !memcmp(events,want,count*sizeof(int)));
        assert(allocation==NULL);
    }
    puts("C: seven actual sigreturn transaction cases passed");return 0;
}
'''


class F06SigreturnTransactionTests(unittest.TestCase):
    def run_checked(self, args):
        r = subprocess.run(args, text=True, capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def test_rust_actual_sigreturn_transaction(self):
        rustc = os.environ.get('RUSTC') or shutil.which('rustc')
        if rustc is None:
            self.skipTest('rustc required for the isolated fixture')
        source = (ROOT/'kernel/rust/syscall_policy.rs').read_text()
        definitions = source[source.index('#[repr(C)]\nstruct RtSigreturnFrame'):source.index('#[no_mangle]\npub unsafe extern "C" fn arch_rt_sigreturn_body_result')]
        with tempfile.TemporaryDirectory(prefix='m14-f06-sigreturn-') as tmp:
            path = Path(tmp)
            code = '#![allow(dead_code,unused_imports,static_mut_refs)]\n'
            code += f'#[path={json.dumps(str(ROOT/"kernel/rust/abi.rs"))}] mod abi;\n'
            code += f'#[path={json.dumps(str(ROOT/"kernel/rust/native_signal.rs"))}] mod native_signal;\n'
            code += RUST + NATIVE + definitions + item(source,'pub unsafe extern "C" fn arch_rt_sigreturn_body_result(')
            (path/'test.rs').write_text(code)
            self.run_checked([rustc,'--edition=2021','--test',str(path/'test.rs'),'-o',str(path/'test')])
            print(self.run_checked([str(path/'test'),'--test-threads=1']).stdout)

    def test_c_actual_sigreturn_transaction(self):
        cc = os.environ.get('CC') or shutil.which('gcc')
        if cc is None:
            self.skipTest('GCC required for the isolated fixture')
        source = (ROOT/'arch/x86_64/kernel/syscall.c').read_text()
        frame = item(source,'struct sigsp {') + ';\n'
        body = item(source,'long sys_rt_sigreturn(int n, ihk_mc_user_context_t *ctx)\n{')
        # Replace instruction endpoints only; all transactions/control flow stay verbatim.
        start = body.index('\tasm ("movq %%gs:')
        end = body.index('\n\t--regs;',start) + len('\n\t--regs;')
        body = body[:start]+'\tregs = fixture_regs;'+body[end:]
        instruction = 'asm volatile("xrstor %0" : : "m"(*kfpregs), "a"(low), "d"(high) : "memory");'
        self.assertIn(instruction,body)
        body = body.replace(instruction,'fixture_restore(kfpregs); (void)low; (void)high;')
        # The production struct is only named, never dereferenced by the observer.
        code = C + frame + '\nstatic int copy_from_user(void *,const void *,size_t);\n' + body + C_CASES
        with tempfile.TemporaryDirectory(prefix='m14-f06-sigreturn-c-') as tmp:
            path=Path(tmp)
            (path/'test.c').write_text(code)
            self.run_checked([cc,'-std=gnu11','-O1','-Wall','-Wextra','-Wno-unused-parameter','-Werror','-fsanitize=undefined',str(path/'test.c'),'-o',str(path/'test')])
            print(self.run_checked([str(path/'test')]).stdout)


if __name__=='__main__':
    unittest.main()
