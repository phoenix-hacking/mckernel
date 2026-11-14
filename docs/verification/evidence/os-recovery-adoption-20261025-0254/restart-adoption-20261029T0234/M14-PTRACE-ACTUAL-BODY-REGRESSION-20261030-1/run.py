#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Host-only isolated actual-body comparison, not a kernel/runtime qualification.
"""
import gzip, hashlib, os, pathlib, re, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[6]
BASE = ROOT / 'docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-SOLMAX-PTRACE-SDK-CHECKPOINT-20261030-1/ptrace-free-log-source-1'
RUST = BASE / 'postimage/kernel/rust/syscall_ptrace_wakeup_logger.rs'
CSRC = BASE / 'postimage/kernel/syscall.c.gz'
HEADER = ROOT / 'lib/include/ihk/debug.h'
expected = {'rust': '4ef213da88797997bf7d7743d651fda6bfc0a090656eaf24211f522b1400cf61', 'c': '5880f20d84640b7afbdc6b14fbc86369d5ec2e68dde1a8d35f111ad28d65b0f4'}
c = gzip.decompress(CSRC.read_bytes())
assert hashlib.sha256(c).hexdigest() == expected['c']
assert hashlib.sha256(RUST.read_bytes()).hexdigest() == expected['rust']
m = re.search(rb'(#line 24424\n\nstatic void\nptrace_wakeup_log_bridge\(int event, int value, int result\)\n\{.*?\n\})\n#endif\n#line 24433', c, re.S)
assert m, 'exact C fallback boundary absent'
callback = m.group(1).decode()
assert hashlib.sha256(HEADER.read_bytes()).hexdigest() == '7315ef758c56c4888242295ed9340b44f649d772b1315502acc49eb6105048dc'
header = HEADER.read_text()
hm = re.search(r'struct ddebug \{.*?\n\} __aligned\(8\);.*?#define ekprintf', header, re.S)
assert hm, 'debug header declaration/macro boundary absent'
header_fragment = hm.group(0).removesuffix('#define ekprintf')
rust_wrapper = '''#![no_std]
use core::panic::PanicInfo;
#[panic_handler] fn panic(_: &PanicInfo) -> ! { loop {} }
mod debug { #[repr(C, align(8))] pub struct Ddebug { pub file: *const i8, pub func: *const i8, pub fmt: *const i8, pub line_flags: u32 } }
mod parent {
    pub type CInt = i32;
    pub const PTRACE_CONTROL_LOG_WAKEUP_ENTER: CInt = 4;
    extern "C" { pub fn kprintf(fmt: *const i8, ...) -> CInt; }
    #[path = "RUSTPATH"] mod logger;
}
'''.replace('RUSTPATH', str(RUST))
runner = r'''
#include <assert.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
int kprintf(const char *format, ...);
#define __aligned(x) __attribute__((aligned(x)))
HEADER_FRAGMENT
#define PTRACE_CONTROL_LOG_WAKEUP_ENTER 4
#if DEFAULT_ON
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#endif
#ifdef ORIGINAL
#line 1 "/src/kernel/syscall.c"
CALLBACK
#else
extern void ptrace_wakeup_log_bridge(int, int, int);
#endif
extern struct ddebug __start___verbose[], __stop___verbose[];
static char output[1024]; static size_t used;
int kprintf(const char *fmt, ...) {
    va_list ap; va_start(ap, fmt); int n = vsnprintf(output + used, sizeof(output) - used, fmt, ap); va_end(ap);
    assert(n >= 0 && (size_t)n < sizeof(output) - used); used += n; return n;
}
int main(void) {
    assert(__stop___verbose - __start___verbose == 1);
    struct ddebug *d = __start___verbose;
    assert(sizeof(*d) == 32 && d->line == 24429 && d->flags == DEFAULT_ON);
    assert(strcmp(d->file, "/src/kernel/syscall.c") == 0);
    assert(strcmp(d->func, "ptrace_wakeup_log_bridge") == 0 && d->fmt == NULL);
    ptrace_wakeup_log_bridge(3, 9, 10); ptrace_wakeup_log_bridge(4, 7, -1);
    if (DEFAULT_ON) assert(strcmp(output, "ptrace_wakeup_sig,pid=7,data=ffffffff\n") == 0);
    else assert(used == 0);
    used = 0; output[0] = 0;
    d->flags = 0;
    ptrace_wakeup_log_bridge(4, 11, 12); assert(used == 0);
    d->flags = 1;
    ptrace_wakeup_log_bridge(4, -1, INT_MIN);
    ptrace_wakeup_log_bridge(-1, 21, 22); ptrace_wakeup_log_bridge(5, 23, 24);
    d->flags = 2;
    ptrace_wakeup_log_bridge(4, INT_MAX, 0);
    d->flags = 0; ptrace_wakeup_log_bridge(4, 25, 26);
    d->flags = 255; ptrace_wakeup_log_bridge(4, 0, 1);
    assert(strcmp(output, "ptrace_wakeup_sig,pid=-1,data=80000000\nptrace_wakeup_sig,pid=2147483647,data=00000000\nptrace_wakeup_sig,pid=0,data=00000001\n") == 0);
    printf("default=%d; descriptor and ordered log sequence PASS\n", DEFAULT_ON);
}
'''.replace('CALLBACK', callback).replace('HEADER_FRAGMENT', header_fragment)

def run(argv, **kwargs):
    print('+', ' '.join(map(str, argv)), flush=True)
    subprocess.run(list(map(str, argv)), check=True, **kwargs)

with tempfile.TemporaryDirectory(prefix='ptrace-body-') as tmp:
    p = pathlib.Path(tmp)
    (p/'wrapper.rs').write_text(rust_wrapper)
    (p/'runner.c').write_text(runner)
    for default in (0, 1):
        env = os.environ.copy(); env['MCKERNEL_F03_PTRACE_WAKEUP_DDEBUG_FLAGS'] = str(default)
        run(['rustc', '+1.85.1', '--edition=2021', '--crate-type=lib', '--emit=obj', '-Cpanic=abort', '-Copt-level=2', p/'wrapper.rs', '-o', p/'logger.o'], env=env)
        for original in (1, 0):
            exe = p / ('c' if original else 'rust')
            argv = ['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-no-pie', '-DDEFAULT_ON='+str(default)]
            if original: argv += ['-DORIGINAL']
            argv += [p/'runner.c']
            if not original: argv += [p/'logger.o']
            run(argv + ['-o', exe]); run([exe])
    for bad in ('2', '', '01'):
        env = os.environ.copy(); env['MCKERNEL_F03_PTRACE_WAKEUP_DDEBUG_FLAGS'] = bad
        result = subprocess.run(['rustc', '+1.85.1', '--edition=2021', '--crate-type=lib', '--emit=obj', '-Cpanic=abort', str(p/'wrapper.rs'), '-o', str(p/'bad.o')], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode != 0 and b'ptrace wakeup debug default must match' in result.stderr, (bad, result.stderr)
        print('invalid Rust default rejected:', repr(bad))
print('PASS: exact C fallback and Rust logger, two defaults, ordered sequential updates, invalid flags')
