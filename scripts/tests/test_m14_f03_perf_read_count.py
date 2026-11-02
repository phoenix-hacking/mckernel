"""Compile the actual C/Rust perf read entries and readers in isolation.

The event/descriptor envelopes and accounting/usercopy endpoints are observation
doubles. Actual source bodies select, size, iterate and copy the response. This
does not qualify production ABI/linkage, event references or concurrent close.
"""
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


C_PREFIX = r'''
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <limits.h>
#include <errno.h>
#include <stdio.h>
#define SYSCALL_POLICY_HELPER_SCOPE
#define PERF_FORMAT_GROUP 8UL
struct list_head { struct list_head *next, *prev; };
struct mc_perf_event {
    struct { unsigned long read_format; } attr;
    struct mc_perf_event *group_leader;
    int nr_siblings;
    struct list_head sibling_list, group_entry;
    unsigned long value;
};
struct mckfd { long data; };
typedef struct { unsigned long args[3]; } ihk_mc_user_context_t;
static unsigned long ihk_mc_syscall_arg1(ihk_mc_user_context_t *ctx) { return ctx->args[1]; }
unsigned long ihk_mc_syscall_arg2(ihk_mc_user_context_t *ctx) { return ctx->args[2]; }
typedef unsigned long (*perf_read_value_fn_t)(void *);
typedef long (*syscall_copy_to_user_fn_t)(unsigned long, const void *, size_t);
typedef long (*perf_read_dispatch_fn_t)(void *, unsigned long, unsigned long);
static int reads, copies, fail_copy;
static unsigned long value(void *event) { reads++; return ((struct mc_perf_event *)event)->value; }
static long copy(unsigned long dst, const void *src, size_t bytes) {
    copies++; if (fail_copy) return -1; memcpy((void *)dst, src, bytes); return 0;
}
'''

C_BRIDGES = r'''
static long perf_event_read_one_bridge(void *event, unsigned long format, unsigned long dst) {
    (void)format; return perf_event_read_one_body_result(event, dst, value, copy);
}
static long perf_event_read_group_bridge(void *event, unsigned long format, unsigned long dst) {
    (void)format; return perf_event_read_group_body_result(event, dst,
        offsetof(struct mc_perf_event, group_leader), offsetof(struct mc_perf_event, nr_siblings),
        offsetof(struct mc_perf_event, sibling_list), offsetof(struct mc_perf_event, group_entry), value, copy);
}
'''

C_CASES = r'''
int main(void) {
    struct mc_perf_event leader = {0}, sibling = {0};
    leader.group_leader = &leader;
    leader.sibling_list.next = &sibling.group_entry;
    sibling.group_entry.next = &leader.sibling_list;
    sibling.group_leader = &leader;
    leader.nr_siblings = 1; leader.value = 111; sibling.value = 222;
    struct mckfd fd = {.data = (long)&sibling};
    for (int group = 0; group < 3; ++group) {
        leader.nr_siblings = group == 1 ? 0 : 1;
        leader.sibling_list.next = group == 1 ? &leader.sibling_list : &sibling.group_entry;
        fd.data = (long)(group == 1 ? &leader : &sibling);
        leader.attr.read_format = PERF_FORMAT_GROUP;
        sibling.attr.read_format = group ? PERF_FORMAT_GROUP : 0;
        unsigned long required = group == 2 ? 24 : group == 1 ? 16 : 8;
        unsigned long counts[] = {0, 1, 7, required - 1, required, required + 1, 64, ULONG_MAX};
        for (unsigned int i = 0; i < sizeof(counts)/sizeof(counts[0]); ++i) {
            unsigned long count = counts[i];
            for (fail_copy = 0; fail_copy < 2; ++fail_copy) {
                _Alignas(unsigned long) unsigned char buf[80]; memset(buf, 0xa5, sizeof(buf)); reads = copies = 0;
                ihk_mc_user_context_t ctx = {.args = {0, (unsigned long)buf, count}};
                long result = perf_read(&fd, &ctx);
                long expected = count < required ? -EINVAL : fail_copy ? -EFAULT : (long)required;
                if (result != expected) { fprintf(stderr, "group=%d count=%lu result=%ld expected=%ld\n", group, count, result, expected); return 1; }
                if (count < required && (reads || copies)) return 2;
                if (count >= required && (!reads || !copies)) return 3;
                unsigned long written = count < required || fail_copy ? 0 : required;
                for (unsigned long j = written; j < sizeof(buf); ++j) if (buf[j] != 0xa5) return 4;
                if (written && ((unsigned long *)buf)[0] != (group ? (unsigned long)leader.nr_siblings + 1 : 222UL)) return 5;
                if (written && group && ((unsigned long *)buf)[1] != 111) return 6;
                if (written && group == 2 && ((unsigned long *)buf)[2] != 222) return 6;
            }
        }
    }
    /* Widen before group sizing: INT_MAX must never wrap into a small read. */
    sibling.attr.read_format = PERF_FORMAT_GROUP;
    for (int nr = 0; nr < 2; ++nr) {
        leader.nr_siblings = nr ? INT_MAX : -1; reads = copies = 0;
        unsigned char buf[80]; memset(buf, 0xa5, sizeof(buf));
        ihk_mc_user_context_t ctx = {.args = {0, (unsigned long)buf, sizeof(buf)}};
        if (perf_read(&fd, &ctx) != -EINVAL || reads || copies) return 7;
    }
    sibling.group_leader = NULL; reads = copies = 0;
    ihk_mc_user_context_t ctx = {.args = {0, 0, ULONG_MAX}};
    if (perf_read(&fd, &ctx) != -EINVAL || reads || copies) return 8;
    return 0;
}
'''

RUST_PREFIX = r'''
#![allow(dead_code, non_upper_case_globals)]
use core::{ffi::c_void, mem::{size_of, offset_of}, ptr::{read_volatile, write_volatile}};
type CInt = i32; type CLong = i64; type CULong = u64; type SizeT = usize;
const EINVAL: i32 = 22; const EFAULT: i32 = 14;
#[repr(C)] struct AbiListHead { next: *mut AbiListHead, prev: *mut AbiListHead }
#[repr(C)] struct Event { read_format: u64, leader: *mut Event, nr: i32, head: AbiListHead, entry: AbiListHead, value: u64 }
struct Mckfd { data: i64 }
struct X86UserContext { args: [u64;3] }
mod x86_cpu_helpers {
    use super::*;
    pub unsafe fn ihk_mc_syscall_arg1(ctx: *mut X86UserContext) -> u64 { (*ctx).args[1] }
    pub unsafe fn ihk_mc_syscall_arg2(ctx: *mut X86UserContext) -> u64 { (*ctx).args[2] }
}
type PerfReadValueFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type SyscallCopyToUserFn = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;
type PerfReadDispatchFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CLong;
static mut READS: usize = 0; static mut COPIES: usize = 0; static mut FAIL: bool = false;
unsafe extern "C" fn value(event: *mut c_void) -> u64 { READS += 1; (*event.cast::<Event>()).value }
unsafe extern "C" fn copy(dst: u64, src: *const u8, bytes: usize) -> i64 {
    COPIES += 1; if FAIL { return -1; } core::ptr::copy_nonoverlapping(src, dst as *mut u8, bytes); 0
}
struct Layout { read_format: usize, group_flag: u64, group_leader: usize, nr_siblings: usize }
static f03_perf_read_layout_v1: Layout = Layout {
    read_format: offset_of!(Event, read_format), group_flag: 8,
    group_leader: offset_of!(Event, leader), nr_siblings: offset_of!(Event, nr),
};
unsafe extern "C" fn f03_perf_read_one_bridge_v1(event: *mut c_void, _:u64, dst:u64) -> i64 {
    perf_event_read_one_body_result(event, dst, Some(value), Some(copy))
}
unsafe extern "C" fn f03_perf_read_group_bridge_v1(event: *mut c_void, _:u64, dst:u64) -> i64 {
    perf_event_read_group_body_result(event, dst, offset_of!(Event, leader), offset_of!(Event, nr),
        offset_of!(Event, head), offset_of!(Event, entry), Some(value), Some(copy))
}
'''

RUST_CASES = r'''
fn main() { unsafe {
    let mut leader: Event = core::mem::zeroed(); let mut sibling: Event = core::mem::zeroed();
    leader.leader = &mut leader; sibling.leader = &mut leader;
    leader.head.next = &mut sibling.entry; sibling.entry.next = &mut leader.head;
    leader.nr = 1; leader.value = 111; sibling.value = 222;
    let mut fd = Mckfd { data: (&mut sibling as *mut Event) as i64 };
    for group in [0, 1, 2] {
        leader.nr = if group == 1 {0} else {1};
        leader.head.next = if group == 1 {&mut leader.head} else {&mut sibling.entry};
        fd.data = if group == 1 {&mut leader} else {&mut sibling} as *mut Event as i64;
        leader.read_format = 8;
        sibling.read_format = if group != 0 {8} else {0};
        let required = if group == 2 {24u64} else if group == 1 {16} else {8};
        for count in [0, 1, 7, required-1, required, required+1, 64, u64::MAX] {
            for fail in [false, true] {
                let mut buf = [0xa5u8; 80]; READS = 0; COPIES = 0; FAIL = fail;
                let mut ctx = X86UserContext { args: [0, buf.as_mut_ptr() as u64, count] };
                let result = f03_perf_read_v1(&mut fd, &mut ctx);
                let expected = if count < required {-22} else if fail {-14} else {required as i64};
                assert_eq!(result, expected, "group={group} count={count} fail={fail}");
                if count < required { assert!(READS == 0 && COPIES == 0); }
                else { assert!(READS != 0 && COPIES != 0); }
                let written = if count < required || fail {0} else {required as usize};
                assert!(buf[written..].iter().all(|b| *b == 0xa5));
                if written != 0 {
                    let first = u64::from_ne_bytes(buf[..8].try_into().unwrap());
                    assert_eq!(first, if group != 0 {leader.nr as u64 + 1} else {222});
                    if group != 0 { assert_eq!(u64::from_ne_bytes(buf[8..16].try_into().unwrap()),111); }
                    if group == 2 { assert_eq!(u64::from_ne_bytes(buf[16..24].try_into().unwrap()),222); }
                }
            }
        }
    }
    sibling.read_format = 8;
    for nr in [-1, i32::MAX] {
        leader.nr = nr; READS = 0; COPIES = 0;
        let mut ctx = X86UserContext { args: [0, 0, 80] };
        assert_eq!(f03_perf_read_v1(&mut fd, &mut ctx), -22); assert!(READS == 0 && COPIES == 0);
    }
    sibling.leader = core::ptr::null_mut(); READS = 0; COPIES = 0;
    let mut ctx = X86UserContext { args: [0, 0, u64::MAX] };
    assert_eq!(f03_perf_read_v1(&mut fd, &mut ctx), -22); assert!(READS == 0 && COPIES == 0);
} }
'''


class PerfReadCountTests(unittest.TestCase):
    def run_fixture(self, language):
        compiler = os.environ.get("RUSTC" if language == "rust" else "CC") or shutil.which("rustc" if language == "rust" else "gcc")
        if compiler is None:
            self.skipTest(language + " compiler unavailable")
        source = (ROOT / ("kernel/rust/syscall_policy.rs" if language == "rust" else "kernel/syscall.c")).read_text()
        names = ["perf_event_read_one_body_result", "perf_event_read_group_body_result", "perf_read_body_result"]
        if language == "rust":
            functions = [item(source, 'pub unsafe extern "C" fn ' + name + '(') for name in names]
            helpers = [item(source, "unsafe fn field_ptr<T>("), item(source, "unsafe fn wait_list_entry(")]
            wrapper = item(source, 'pub unsafe extern "C" fn f03_perf_read_v1(')
            # The actual entry lives one module down in production.
            body = RUST_PREFIX + '\n'.join(helpers + functions) + "\nmod entry { use super::*;\n" + wrapper + "\n}\nuse entry::f03_perf_read_v1;\n" + RUST_CASES
            args = [compiler, "--edition=2021", "-Awarnings"]
            suffix = ".rs"
        else:
            functions = [item(source, "long\n" + name + '(') for name in names]
            wrapper = item(source, "static long\nperf_read(")
            body = C_PREFIX + '\n'.join(functions) + C_BRIDGES + wrapper + C_CASES
            args = [compiler, "-std=gnu11", "-O0", "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined"]
            suffix = ".c"
        with tempfile.TemporaryDirectory(prefix="m14-perf-count-") as directory:
            path = Path(directory)
            fixture, binary = path / ("fixture" + suffix), path / "fixture"
            fixture.write_text(body)
            result = subprocess.run(args + [str(fixture), "-o", str(binary)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_c_count_bounds(self):
        self.run_fixture("c")

    def test_rust_count_bounds(self):
        self.run_fixture("rust")


if __name__ == "__main__":
    unittest.main()
