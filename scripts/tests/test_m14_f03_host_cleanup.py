"""Exercise real C/Rust host cleanup bodies with observable lifetime providers.

These are ordinary HOST fixtures. Rust uses the genuine ABI/lock types; C uses
small observation structures. Provider order, exactly-once kill, lock pairing and
capturing the process before thread release are checked independently. This does
not establish production provider linkage, kernel-layout or native qualification.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.tests.test_m14_f06_tail_codegen import definition


ROOT = Path(__file__).resolve().parents[2]
RUST = ROOT / "kernel/rust"


def c_definition(source, name):
    match = re.search(r"^(?:SYSCALL_POLICY_HELPER_SCOPE\s+)?(?:int|long|void)\s+"
                      + name + r"\([^;{}]*\)\s*\{", source, re.M)
    if match is None:
        raise ValueError("missing unique C body: " + name)
    opening = source.index("{", match.start())
    end, depth = opening + 1, 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end]


RUST_OBSERVER = r'''
use std::cell::RefCell;
use abi::*;
struct State {
    cpu: *mut CpuLocalVar, process: *mut Process, detached: *mut Thread,
    found: bool, pid: i32, initial: i32, result: i64,
    lock: *mut core::ffi::c_void, events: Vec<i32>,
}
thread_local! { static STATE: RefCell<Option<State>> = const { RefCell::new(None) }; }
fn observe(f: impl FnOnce(&mut State)) { STATE.with(|s| f(s.borrow_mut().as_mut().unwrap())); }
#[no_mangle]
unsafe extern "C" fn get_this_cpu_local_var() -> *mut CpuLocalVar {
    STATE.with(|s| s.borrow().as_ref().unwrap().cpu)
}
#[no_mangle]
unsafe extern "C" fn syscall_find_process_bridge(pid: i32, lock: *mut core::ffi::c_void)
    -> *mut core::ffi::c_void {
    let mut result = core::ptr::null_mut();
    observe(|s| {
        assert_eq!(pid, s.pid); assert!(!lock.is_null()); assert_eq!(lock as usize % 64, 0);
        s.lock = lock; s.events.push(1);
        if s.found { result = s.process.cast(); }
    });
    result
}
#[no_mangle]
unsafe extern "C" fn syscall_process_unlock_bridge(process: *mut core::ffi::c_void,
                                                    lock: *mut core::ffi::c_void) {
    observe(|s| {
        assert_eq!(process, s.process.cast()); assert_eq!(lock, s.lock);
        assert_eq!((*s.process).nohost, 1); s.events.push(2);
    });
}
#[no_mangle]
unsafe extern "C" fn f03_terminate_host_refcount_set_v1(ptr: *mut core::ffi::c_void, value: i32) {
    observe(|s| {
        assert_eq!(ptr, core::ptr::addr_of_mut!((*s.detached).refcount).cast());
        assert_eq!(value, 1); ptr.cast::<i32>().write(value); s.events.push(3);
    });
}
#[no_mangle]
unsafe extern "C" fn f03_wait_release_thread(thread: *mut core::ffi::c_void) {
    observe(|s| {
        assert_eq!(thread, s.detached.cast());
        assert_eq!(core::ptr::addr_of!((*s.detached).refcount).cast::<i32>().read(), 1);
        // Poison released state so a later process lookup through thread fails.
        (*s.detached).proc = core::ptr::null_mut(); s.events.push(4);
    });
}
#[no_mangle]
unsafe extern "C" fn f03_wait_release_process(process: *mut core::ffi::c_void) {
    observe(|s| { assert_eq!(process, s.process.cast()); s.events.push(5); });
}
#[no_mangle]
unsafe extern "C" fn syscall_do_kill_thread_bridge(thread: *mut core::ffi::c_void,
    pid: i32, tid: i32, sig: i32, info: *const SigInfo, cont: i32) -> i64 {
    let mut result = 0;
    observe(|s| {
        assert_eq!(s.events, [1, 2]); assert_eq!(thread, (*s.cpu).current.cast());
        assert_eq!((pid, tid, sig, cont), (s.pid, -1, 9, 0)); assert!(info.is_null());
        s.events.push(6); result = s.result;
    });
    result
}
unsafe fn storage<T>() -> *mut T {
    let p = std::alloc::alloc_zeroed(std::alloc::Layout::new::<T>()).cast::<T>();
    assert!(!p.is_null()); p
}
unsafe fn discard<T>(p: *mut T) { std::alloc::dealloc(p.cast(), std::alloc::Layout::new::<T>()); }
fn main() { unsafe {
    let mut cases = 0;
    for pid in [i32::MIN, -1, 1, i32::MAX] {
    for result in [0, -1, -4095, i64::MIN] {
    for initial in [0, 1, 2, -1] {
    for found in [false, true] {
    for has_detached in [false, true] {
        let cpu = storage::<CpuLocalVar>(); let process = storage::<Process>();
        let thread = storage::<Thread>(); let current = storage::<Thread>();
        (*cpu).current = current; (*thread).proc = process; (*process).nohost = initial;
        let detached = if has_detached { thread } else { core::ptr::null_mut() };
        STATE.with(|s| *s.borrow_mut() = Some(State {
            cpu, process, detached, found, pid, initial, result,
            lock: core::ptr::null_mut(), events: Vec::new(),
        }));
        candidate::terminate_host(pid, detached);
        observe(|s| {
            let expected: &[i32] = if found {
                if s.initial == 1 { &[1, 2] } else { &[1, 2, 6] }
            } else if has_detached { &[1, 3, 4, 5] } else { &[1] };
            assert_eq!(s.events, expected);
            assert_eq!((*process).nohost, if found { 1 } else { initial });
        });
        if found {
            candidate::terminate_host(pid, detached);
            observe(|s| {
                let expected: &[i32] = if initial == 1 { &[1, 2, 1, 2] }
                                      else { &[1, 2, 6, 1, 2] };
                assert_eq!(s.events, expected);
            });
        }
        STATE.with(|s| *s.borrow_mut() = None);
        discard(cpu); discard(process); discard(thread); discard(current); cases += 1;
    }}}}}
    println!("PASS {cases} cleanup cases");
}}
'''


C_OBSERVER = r'''
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#define SYSCALL_POLICY_HELPER_SCOPE
#define SIGKILL 9
struct process { int nohost; };
struct thread { struct process *proc; int refcount; };
struct mcs_rwlock_node_irqsave { unsigned long irqsave; } __attribute__((aligned(64)));
struct cpu_local_var { struct thread *current; };
struct siginfo;
@TYPEDEFS@
@HELPERS@
static struct cpu_local_var cpu;
static struct process process;
static struct thread current, detached;
static int found, want_pid, events[8], count;
static void *lookup_lock;
static long kill_result;
#define require(x) do { if (!(x)) abort(); } while (0)
static void event(int value) { require(count < 8); events[count++] = value; }
static struct cpu_local_var *get_this_cpu_local_var(void) { return &cpu; }
static void *syscall_find_process_bridge(int pid, void *lock) {
    require(pid == want_pid && lock && (uintptr_t)lock % 64 == 0);
    lookup_lock = lock; event(1); return found ? &process : NULL;
}
static void syscall_process_unlock_bridge(void *proc, void *lock) {
    require(proc == &process && lock == lookup_lock && process.nohost == 1); event(2);
}
static void terminate_host_refcount_set_bridge(void *ptr, int value) {
    require(ptr == &detached.refcount && value == 1); *(int *)ptr = value; event(3);
}
static void wait_thread_release_bridge(void *thread) {
    require(thread == &detached && detached.refcount == 1); detached.proc = NULL; event(4);
}
static void wait_process_release_bridge(void *proc) { require(proc == &process); event(5); }
static long syscall_do_kill_thread_bridge(void *thread, int pid, int tid, int sig,
                                          const void *info, int cont) {
    require(count == 2 && events[0] == 1 && events[1] == 2);
    require(thread == &current && pid == want_pid && tid == -1 && sig == 9 && !info && !cont);
    event(6); return kill_result;
}
@BODY@
int main(void) {
    const int pids[] = {INT_MIN, -1, 1, INT_MAX}, initial[] = {0, 1, 2, -1};
    const long results[] = {0, -1, -4095, LONG_MIN};
    int cases = 0; cpu.current = &current;
    for (int p = 0; p < 4; ++p) for (int r = 0; r < 4; ++r)
    for (int n = 0; n < 4; ++n) for (found = 0; found < 2; ++found)
    for (int has_detached = 0; has_detached < 2; ++has_detached) {
        want_pid = pids[p]; kill_result = results[r]; process.nohost = initial[n];
        detached.proc = &process; detached.refcount = 7; count = 0;
        terminate_host(want_pid, has_detached ? &detached : NULL);
        require(events[0] == 1);
        if (found) {
            require(count == (initial[n] == 1 ? 2 : 3) && events[1] == 2);
            if (initial[n] != 1) require(events[2] == 6);
            require(process.nohost == 1);
            int first_count = count;
            terminate_host(want_pid, has_detached ? &detached : NULL);
            require(count == first_count + 2 && events[first_count] == 1 && events[first_count+1] == 2);
        } else if (has_detached) {
            require(count == 4 && events[1] == 3 && events[2] == 4 && events[3] == 5);
        } else require(count == 1);
        if (!found) require(process.nohost == initial[n]);
        ++cases;
    }
    printf("PASS %d cleanup cases\n", cases); return 0;
}
'''


class HostCleanupTests(unittest.TestCase):
    def checked(self, command):
        result = subprocess.run(command, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_actual_source_guard_keeps_one_entry_owner(self):
        cc = os.environ.get("CC") or shutil.which("gcc")
        if not cc:
            self.skipTest("C compiler required")
        source = (ROOT / "kernel/syscall.c").read_text()
        start = source.index("#ifdef MCKERNEL_RUST_F03_FORWARD_ADAPTERS\n"
                             "extern void terminate_host(")
        closing = "#endif /* MCKERNEL_RUST_F03_FORWARD_ADAPTERS */"
        guard = source[start:source.index(closing, start) + len(closing)]
        # Calls into the fallback body are opaque observations in this object
        # check; only the actual entry selector is under examination.
        fixture = r'''
#include <stddef.h>
struct thread;
struct process { int nohost; };
struct thread { struct process *proc; int refcount; };
struct mcs_rwlock_node_irqsave { unsigned long irqsave; };
struct cpu_local_var { struct thread *current; };
extern struct cpu_local_var *get_this_cpu_local_var(void);
extern long observe_body(void);
#define terminate_host_body_result(...) observe_body()
@GUARD@
void (*const entry)(int, struct thread *) = terminate_host;
'''.replace("@GUARD@", guard)
        with tempfile.TemporaryDirectory(prefix="m14-cleanup-owner-") as temporary:
            path = Path(temporary)
            csource = path / "guard.c"
            csource.write_text(fixture)
            for selected in (False, True):
                obj = path / f"{selected}.o"
                command = [cc, "-O0", "-c", str(csource), "-o", str(obj)]
                if selected:
                    command.append("-DMCKERNEL_RUST_F03_FORWARD_ADAPTERS=1")
                self.checked(command)
                symbols = self.checked(["nm", "--format=posix", str(obj)])
                matches = [line.split()[1] for line in symbols.splitlines()
                           if line.split()[0] == "terminate_host"]
                self.assertEqual(matches, ["U" if selected else "T"])

    def test_real_cleanup_bodies_preserve_lifetime_and_notification_order(self):
        cc = os.environ.get("CC") or shutil.which("gcc")
        rustc = os.environ.get("RUSTC") or shutil.which("rustc")
        if not cc or not rustc:
            self.skipTest("C and Rust compilers required")
        c = (ROOT / "kernel/syscall.c").read_text()
        policy = (RUST / "syscall_policy.rs").read_text()
        names = ("process_lookup_missing_result",
                 "terminate_host_detached_thread_release_needed_result",
                 "terminate_host_kill_needed_result", "terminate_host_body_result")
        aliases = ("SyscallFindProcessFn", "SyscallProcessUnlockFn", "TerminateHostRefSetFn",
                   "WaitThreadSideEffectFn", "SyscallDoKillThreadFn")
        types = []
        for name in aliases:
            types.append(re.search(r"(?m)^type " + name + r"\s*=[^;]+;", policy).group())
        constants = [re.search(r"(?m)^const " + name + r"\s*:[^;]+;", policy).group()
                     for name in ("EINVAL", "SIGKILL")]
        node = definition((RUST / "lock_helpers.rs").read_text(), "McsRwlockNodeIrqsave", "struct")
        rust = ('#![allow(dead_code,unused_imports)]\n'
                f'#[path="{RUST / "abi.rs"}"] mod abi;\n'
                'mod lock_helpers { use crate::abi::*; #[repr(C,align(64))]\n' + node + '\n}\n'
                'mod cls { use crate::abi::*; unsafe extern "C" {\n'
                'pub fn get_this_cpu_local_var() -> *mut CpuLocalVar; } }\n'
                'mod syscall_policy { use crate::abi::*; use core::ffi::c_void;\n'
                'use core::ptr::{read_volatile,write_volatile};\n'
                + '\n'.join(types + constants + [definition(policy, "field_ptr")]
                            + [definition(policy, name) for name in names]) + '\n}\n'
                f'#[path="{RUST / "f03_host_cleanup.rs"}"] mod candidate;\n'
                'const _: unsafe extern "C" fn(abi::CInt,*mut abi::Thread) = candidate::terminate_host;\n'
                + RUST_OBSERVER)
        c_types = []
        for name in ("syscall_find_process_fn_t", "syscall_process_unlock_fn_t",
                     "terminate_host_ref_set_fn_t", "wait_thread_side_effect_fn_t",
                     "syscall_do_kill_thread_fn_t"):
            c_types.append(re.search(r"typedef\s+[^;]*\(\*" + name + r"\)[^;]*;", c).group())
        c_source = C_OBSERVER.replace("@TYPEDEFS@", '\n'.join(c_types)) \
            .replace("@HELPERS@", '\n'.join(c_definition(c, name) for name in names)) \
            .replace("@BODY@", c_definition(c, "terminate_host"))
        with tempfile.TemporaryDirectory(prefix="m14-host-cleanup-") as temporary:
            path = Path(temporary)
            rsource, csource = path / "fixture.rs", path / "fixture.c"
            rsource.write_text(rust); csource.write_text(c_source)
            for language, source, command in (
                ("C", csource, [cc, "-std=gnu11", "-Werror=incompatible-pointer-types",
                                "-fsanitize=undefined", "-fno-sanitize-recover=all"]),
                ("Rust", rsource, [rustc, "--edition=2021", "-C", "opt-level=2"]),
            ):
                with self.subTest(language=language):
                    binary = path / language
                    self.checked([*command, str(source), "-o", str(binary)])
                    self.assertEqual(self.checked([str(binary)]), "PASS 256 cleanup cases\n")


if __name__ == "__main__":
    unittest.main()
