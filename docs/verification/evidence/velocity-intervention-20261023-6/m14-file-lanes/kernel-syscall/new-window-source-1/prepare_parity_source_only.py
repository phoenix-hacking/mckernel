"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Create controlled fixture sources only. Never invoke a compiler or fixture here.
"""
from pathlib import Path
import hashlib
import json
import re

D = Path(__file__).resolve().parent
R = Path('/home/holden/mckernel')
policy = (R / 'kernel/rust/syscall_policy.rs').read_text()
abi = (R / 'kernel/rust/abi.rs').read_text()

def block(source, start):
    begin = source.index(start)
    opening = source.index('{', begin)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[begin:end]

def put(name, text):
    with (D / name).open('x') as stream:
        stream.write(text)

structs = '\n\n'.join('#[repr(C)]\n' + block(abi, 'pub struct ' + name + ' {')
                       for name in ['X86BasicRegs', 'X86Sregs', 'X86UserContext'])
wrappers = '\n\n'.join('#[no_mangle]\n' + block(policy, 'pub unsafe extern "C" fn ' + name + '(')
                         for name in ['sys_swapout', 'sys_linux_mlock'])
put('ACTUAL-SELECTED-RUST-WRAPPERS.rs.inc', wrappers + '\n')
put('ACTUAL-CONTEXT-ABI.rs.inc', structs + '\n')
put('parity.rs', r'''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code)]
use core::ffi::c_void;
use core::mem::MaybeUninit;
use abi::{CInt, CLong, CULong, SizeT, X86UserContext};
mod abi {
    pub type CInt = i32;
    pub type CLong = i64;
    pub type CULong = u64;
    pub type SizeT = usize;
    include!("ACTUAL-CONTEXT-ABI.rs.inc");
}
mod debug {
    #[repr(C)]
    pub struct Ddebug {
        pub file: *const i8,
        pub func: *const i8,
        pub fmt: *const i8,
        pub line_flags: u32,
    }
}
const EFAULT: CInt = 14;
const SYS_SWAPOUT: CInt = 801;
const SYS_LINUX_MLOCK: CInt = 802;
type Out = unsafe extern "C" fn(*const c_void, *mut c_void, SizeT, CInt) -> CInt;
type In = unsafe extern "C" fn(CInt) -> CInt;
type Forward = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;
type Sys2 = unsafe extern "C" fn(CInt, CULong, CULong) -> CLong;
unsafe extern "C" {
    fn kprintf(format: *const i8, ...) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn syscall_swapout_log_bridge(a: *const c_void, b: *mut c_void, c: SizeT, d: CInt);
    fn syscall_linux_mlock_log_bridge(a: CULong, b: SizeT);
    fn fixture_body_record(kind: CInt, a: CULong, b: CULong, c: CULong, d: CLong) -> CLong;
}
include!("io_diagnostics.RUST-FRAGMENT.rs.inc");
include!("ACTUAL-SELECTED-RUST-WRAPPERS.rs.inc");
unsafe extern "C" fn do_pageout(_: *const c_void, _: *mut c_void, _: SizeT, _: CInt) -> CInt { -97 }
unsafe extern "C" fn do_pagein(_: CInt) -> CInt { -97 }
unsafe extern "C" fn syscall_policy_forward_context_bridge(_: CInt, _: *mut c_void) -> CLong { -97 }
unsafe extern "C" fn syscall_policy_do_syscall2_bridge(_: CInt, _: CULong, _: CULong) -> CLong { -97 }
// Controlled downstream providers observe the genuine wrapper boundary only.
unsafe fn swapout_body_result(a: *const c_void, b: *mut c_void, c: SizeT, d: CInt,
    nr: CInt, ctx: *mut c_void, out: Option<Out>, input: Option<In>, fwd: Option<Forward>) -> CLong {
    assert_eq!(nr, SYS_SWAPOUT);
    assert!(!ctx.is_null() && out.is_some() && input.is_some() && fwd.is_some());
    unsafe { fixture_body_record(1, a as CULong, b as CULong, c as CULong, d as CLong) }
}
unsafe fn linux_mlock_body_result(a: CULong, b: SizeT, nr: CInt, f: Option<Sys2>) -> CLong {
    assert_eq!(nr, SYS_LINUX_MLOCK);
    assert!(f.is_some());
    unsafe { fixture_body_record(2, a, b as CULong, 0, 0) }
}
#[no_mangle]
pub unsafe extern "C" fn fixture_rust_wrapper(kind: CInt, a: CULong, b: CULong,
    c: CULong, d: CInt, null_context: CInt) -> CLong {
    let mut ctx: X86UserContext = unsafe { core::mem::zeroed() };
    ctx.gpr.rdi = a;
    ctx.gpr.rsi = b;
    ctx.gpr.rdx = c;
    ctx.gpr.r10 = d as CULong;
    let pointer = if null_context != 0 { core::ptr::null_mut() } else { &mut ctx };
    unsafe { if kind == 1 { sys_swapout(801, pointer) } else { sys_linux_mlock(802, pointer) } }
}
''')
original = (D / 'ACTUAL-ORIGINAL-C.inc').read_text()
original = original.replace('syscall_swapout_log_bridge(', 'original_swapout(')
original = original.replace('syscall_linux_mlock_log_bridge(', 'original_mlock(')
put('parity.c', r'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <assert.h>
#include <limits.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
/* Keep the actual project debug macro/record, adapting only its include dependency. */
#define __LWK_COMPILER_H
#define __aligned(x) __attribute__((aligned(x)))
#include <ihk/debug.h>
struct ddebug __attribute__((aligned(8),section("__verbose"))) f03_swapout_callback_debug_v1;
extern struct ddebug __start___verbose[], __stop___verbose[];
extern void syscall_swapout_log_bridge(const void *, void *, size_t, int);
extern void syscall_linux_mlock_log_bridge(unsigned long, unsigned long);
extern long fixture_rust_wrapper(int, unsigned long, unsigned long, unsigned long, int, int);
struct observation {
    char format[80], bytes[256], events[8];
    unsigned long slots[5], body[4];
    int used, prints, cpus, bodies, kind;
};
static struct observation observed;
static void event(char c) { assert(observed.used < 7); observed.events[observed.used++] = c; }
static void reset(void) { memset(&observed, 0, sizeof(observed)); }
int ihk_mc_get_processor_id(void) { event('C'); observed.cpus++; return 19; }
int kprintf(const char *format, ...) {
    va_list ap, render;
    event('P'); observed.prints++;
    assert(observed.prints == 1 && strlen(format) < sizeof(observed.format));
    strcpy(observed.format, format);
    va_start(ap, format); va_copy(render, ap);
    int n = vsnprintf(observed.bytes, sizeof(observed.bytes), format, render);
    va_end(render);
    assert(n >= 0 && (size_t)n < sizeof(observed.bytes));
    if (strcmp(format, "[%d]swapout(%lx,%lx,%lx,%ld)\n") == 0) {
        observed.slots[0] = (unsigned long)va_arg(ap, int);
        observed.slots[1] = va_arg(ap, unsigned long);
        observed.slots[2] = va_arg(ap, unsigned long);
        observed.slots[3] = va_arg(ap, unsigned long);
        observed.slots[4] = (unsigned long)va_arg(ap, long);
    } else {
        assert(strcmp(format, "linux_mlock: %p %ld\n") == 0);
        observed.slots[0] = (unsigned long)va_arg(ap, void *);
        observed.slots[1] = (unsigned long)va_arg(ap, long);
    }
    va_end(ap); return n;
}
long fixture_body_record(int kind, unsigned long a, unsigned long b, unsigned long c, long d) {
    event('B'); observed.bodies++; observed.kind = kind;
    observed.body[0] = a; observed.body[1] = b; observed.body[2] = c; observed.body[3] = (unsigned long)d;
    return -73;
}
''' + original + r'''
static int equal(const struct observation *a, const struct observation *b) {
    return strcmp(a->format,b->format)==0 && strcmp(a->bytes,b->bytes)==0 &&
        strcmp(a->events,b->events)==0 && memcmp(a->slots,b->slots,sizeof(a->slots))==0 &&
        memcmp(a->body,b->body,sizeof(a->body))==0 && a->used==b->used &&
        a->prints==b->prints && a->cpus==b->cpus && a->bodies==b->bodies && a->kind==b->kind;
}
static void flags(unsigned int value) {
    for (struct ddebug *p = __start___verbose; p < __stop___verbose; p++) p->flags = value;
}
int main(void) {
    const unsigned long values[] = {0, 1, LONG_MAX, (unsigned long)LONG_MAX + 1, ULONG_MAX};
    const int flag_values[] = {0, -1, INT_MIN, INT_MAX};
    const unsigned int debug_flags[] = {0, 1, 128};
    unsigned int cases = 0;
    assert(sizeof(unsigned long) == 8 && sizeof(long) == 8 && sizeof(size_t) == 8);
    assert(sizeof(struct ddebug) == 32 && _Alignof(struct ddebug) == 8);
    assert(__stop___verbose - __start___verbose == 2);
    for (unsigned int f = 0; f < 3; f++) {
        flags(debug_flags[f]);
        for (unsigned int a = 0; a < 5; a++) for (unsigned int b = 0; b < 5; b++) {
            for (unsigned int d = 0; d < 4; d++) {
                const unsigned long x = values[a], y = values[b], size = values[(a+b)%5];
                const int flag = flag_values[d];
                reset(); original_swapout((void *)x, (void *)y, size, flag);
                struct observation expected = observed;
                assert(expected.cpus == (f != 0) && expected.prints == (f != 0));
                if (f) {
                    assert(strcmp(expected.events, "CP") == 0);
                    assert(expected.slots[0] == 19 && expected.slots[1] == x);
                    assert(expected.slots[2] == y && expected.slots[3] == size);
                    assert(expected.slots[4] == (unsigned long)(long)flag);
                }
                reset(); syscall_swapout_log_bridge((void *)x, (void *)y, size, flag);
                assert(equal(&expected, &observed));
                reset(); assert(fixture_rust_wrapper(1, x, y, size, flag, 0) == -73);
                assert(strcmp(observed.events, f ? "CPB" : "B") == 0);
                assert(observed.bodies == 1 && observed.kind == 1);
                assert(observed.body[0] == x && observed.body[1] == y);
                assert(observed.body[2] == size && observed.body[3] == (unsigned long)(long)flag);
                observed.events[expected.used] = 0;
                observed.used = expected.used; observed.bodies = 0; observed.kind = 0;
                memset(observed.body, 0, sizeof(observed.body));
                assert(equal(&expected, &observed));
                cases++;
            }
            reset(); original_mlock(values[a], values[b]); struct observation expected = observed;
            assert(strcmp(expected.events, "P") == 0 && expected.cpus == 0 && expected.prints == 1);
            assert(expected.slots[0] == values[a] && expected.slots[1] == values[b]);
            reset(); syscall_linux_mlock_log_bridge(values[a], values[b]);
            assert(equal(&expected, &observed));
            reset(); assert(fixture_rust_wrapper(2, values[a], values[b], 0, 0, 0) == -73);
            assert(strcmp(observed.events, "PB") == 0 && observed.bodies == 1 && observed.kind == 2);
            assert(observed.body[0] == values[a] && observed.body[1] == values[b]);
            observed.events[expected.used] = 0; observed.used = expected.used;
            observed.bodies = 0; observed.kind = 0; memset(observed.body, 0, sizeof(observed.body));
            assert(equal(&expected, &observed)); cases++;
        }
    }
    for (int kind = 1; kind <= 2; kind++) {
        reset(); assert(fixture_rust_wrapper(kind, 0, 0, 0, 0, 1) == -14);
        struct observation empty = {0}; assert(equal(&empty, &observed));
    }
    printf("PASS controlled diagnostic parity %u vectors plus 2 null-context wrappers\n", cases);
    return 0;
}
''')
files = ['prepare_parity_source_only.py', 'parity.rs', 'parity.c',
         'ACTUAL-SELECTED-RUST-WRAPPERS.rs.inc', 'ACTUAL-CONTEXT-ABI.rs.inc',
         'io_diagnostics.RUST-FRAGMENT.rs.inc']
manifest = {
    'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
    'status': 'CONTROLLED_PARITY_FIXTURE_SOURCE_ONLY_NOT_COMPILED_NOT_RUN',
    'vectors_expected': 375,
    'null_context_cases_expected': 2,
    'actual_wrapper_sources': ['sys_swapout', 'sys_linux_mlock'],
    'controlled_providers': ['kprintf captures exact format/scalar ABI and host rendered bytes',
                             'ihk_mc_get_processor_id returns19 and records conditional invocation',
                             'body_result providers record args/order and return-73; no pageout/offload'],
    'real_header': 'lib/include/ihk/debug.h included; compiler dependency shim only',
    'limits': 'One ordinary unprivileged CPU, AS2GiB, no core, FD256, file32MiB, stack2MiB; compiler CPU60/wall90; executable CPU10/wall15.',
    'required_grant': 'Coordinator actual physical clearance and ordinary compiler/execution grant; not supplied.',
    'native_default_or_fullfile_credit': False,
    'remaining': 'Full actual selected/fallback syscall TU and real-header ABI witness remain separate checks.',
    'files': [{'path': str(D / name), 'sha256': hashlib.sha256((D / name).read_bytes()).hexdigest()}
              for name in files],
}
put('PARITY-FIXTURE-SOURCE-HANDOFF.HOLD.json', json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(json.dumps({'source_only_files': len(files), 'execution': False}))
