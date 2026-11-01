"""Actual C/Rust boot polling with explicit synthetic ioctl/FD/sleep observers.

This compiles only the retained C ihk_os_boot function or actual Rust load/boot
module. No real OS instance, device, timing delay, complete library or module is
used. Status sequences verify bounded polling and the first terminal result.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
C_SOURCE = REPO / 'ihk/linux/user/ihklib.c'
RUST_SOURCE = REPO / 'ihk/linux/user/rust/whole70/ihklib_os_load_boot.rs'

OBSERVER = r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
static int opened, boot_result, boot_errno;
static int open_calls, boot_calls, status_calls, sleep_calls, close_calls;
static int statuses[64], errors[64], length;
int observed_open(int index) { assert(index == 7); ++open_calls; return opened; }
int observed_ioctl(int fd, unsigned long request, ...) {
    assert(fd == opened && fd >= 0);
    if (request == 0x112a01) { ++boot_calls; errno = boot_errno; return boot_result; }
    assert(request == 0x112a14);
    int i = status_calls++;
    assert(length > 0);
    if (i >= length) i = length - 1;
    errno = errors[i];
    return statuses[i];
}
int observed_sleep(unsigned int usec) {
    assert(usec == 200000); ++sleep_calls; errno = EINTR; return -1;
}
int observed_close(int fd) {
    assert(fd == opened && fd >= 0); ++close_calls; errno = EBADF; return -1;
}
#ifdef RUST_OBSERVER
int __wrap_ioctl(int fd, unsigned long request, ...) { return observed_ioctl(fd, request); }
int __wrap_usleep(unsigned int usec) { return observed_sleep(usec); }
int __wrap_close(int fd) { return observed_close(fd); }
#endif
extern int invoke_boot(void);
int main(int argc, char **argv) {
    assert(argc == 5);
    opened = atoi(argv[1]); boot_result = atoi(argv[2]); boot_errno = atoi(argv[3]);
    for (char *token = strtok(argv[4], ","); token; token = strtok(NULL, ",")) {
        assert(length < 64 && sscanf(token, "%d:%d", statuses+length, errors+length) == 2);
        ++length;
    }
    int result = invoke_boot();
    printf("OBS %d %d %d %d %d %d\n", result, open_calls, boot_calls,
           status_calls, sleep_calls, close_calls);
    return 0;
}
'''

RUST_ROOT = r'''
mod ihklib_mcstat {
    unsafe extern "C" { fn observed_open(index: core::ffi::c_int) -> core::ffi::c_int; }
    pub unsafe fn ihklib_os_open(index: core::ffi::c_int) -> core::ffi::c_int {
        unsafe { observed_open(index) }
    }
}
#[path = "__SOURCE__"]
mod actual;
#[no_mangle]
pub unsafe extern "C" fn invoke_boot() -> core::ffi::c_int {
    unsafe { actual::ihk_os_boot(7) }
}
'''


def function(source, marker):
    start = source.index(marker)
    depth, end = 1, source.index('{', start) + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


class IhklibBootPollTests(unittest.TestCase):
    def command(self, arguments):
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def build(self, directory, language):
        cc = shutil.which(os.environ.get('CC') or 'cc')
        self.assertIsNotNone(cc, 'bind CC to a C compiler')
        source, binary = directory / 'observer.c', directory / 'observer'
        if language == 'c':
            source.write_text(OBSERVER + r'''
#include <ihk/status.h>
#define IHK_OS_BOOT 0x112a01
#define IHK_OS_STATUS 0x112a14
#define dprintk(...) ((void)0)
#define dprintf(...) ((void)0)
#define ihklib_os_open observed_open
#define ioctl observed_ioctl
#define usleep observed_sleep
#define close observed_close
''' + function(C_SOURCE.read_text(), 'int ihk_os_boot(') +
                              '\nint invoke_boot(void) { return ihk_os_boot(7); }\n')
            self.command([cc, '-std=c11', '-Wall', '-Wextra', '-Werror',
                          '-I' + str(REPO / 'ihk/linux/include'), str(source), '-o', str(binary)])
        else:
            rustc = shutil.which(os.environ.get('RUSTC') or 'rustc')
            self.assertIsNotNone(rustc, 'bind RUSTC to the qualified compiler')
            root, archive = directory / 'actual.rs', directory / 'actual.a'
            root.write_text(RUST_ROOT.replace('__SOURCE__', str(RUST_SOURCE)))
            self.command([rustc, '--edition=2021', '--crate-type=staticlib', '-C', 'panic=abort',
                          str(root), '-o', str(archive)])
            source.write_text(OBSERVER)
            self.command([cc, '-DRUST_OBSERVER', '-std=c11', '-Wall', '-Wextra', '-Werror',
                          str(source), str(archive), '-Wl,--wrap=ioctl', '-Wl,--wrap=usleep',
                          '-Wl,--wrap=close', '-ldl', '-lpthread', '-lm', '-o', str(binary)])
        return binary

    def cases(self, binary):
        # opened FD, boot ret/errno, status/errno sequence,
        # expected result/open/boot/status/sleep/close counts.
        cases = [
            (9, 0, 0, [(5, 0), (9, 0)], (0, 1, 1, 1, 0, 1)),
            (0, 0, 0, [(5, 0), (9, 0)], (0, 1, 1, 1, 0, 1)),
            (9, 0, 0, [(-1, 5), (5, 0)], (-5, 1, 1, 1, 0, 1)),
            (9, 0, 0, [(2, 0), (-1, 12), (5, 0)], (-12, 1, 1, 2, 1, 1)),
            (9, 0, 0, [(2, 0), (3, 0), (4, 0), (5, 0), (9, 0)], (0, 1, 1, 4, 3, 1)),
            (9, 0, 0, [(2, 0)], (-22, 1, 1, 50, 50, 1)),
            (9, 0, 0, [(4, 0)] * 49 + [(5, 0)], (0, 1, 1, 50, 49, 1)),
            (9, -1, 16, [], (-16, 1, 1, 0, 0, 1)),
            (-1, 0, 0, [], (-1, 1, 0, 0, 0, 0)),
        ]
        for status in (0, 1, 6, 7, 8, 9, 10, 11):
            cases.append((9, 0, 0, [(status, 0), (5, 0)], (-22, 1, 1, 1, 0, 1)))
        for number, (fd, boot_result, boot_errno, statuses, expected) in enumerate(cases):
            with self.subTest(case=number):
                sequence = ','.join(f'{status}:{error}' for status, error in statuses)
                stdout = self.command([str(binary), str(fd), str(boot_result), str(boot_errno), sequence])
                self.assertEqual(tuple(map(int, stdout.removeprefix('OBS ').split())), expected)

    def test_actual_c_boot_polling(self):
        with tempfile.TemporaryDirectory(prefix='m15-boot-poll-c-') as temporary:
            self.cases(self.build(Path(temporary), 'c'))

    def test_actual_rust_boot_polling(self):
        with tempfile.TemporaryDirectory(prefix='m15-boot-poll-rust-') as temporary:
            self.cases(self.build(Path(temporary), 'rust'))


if __name__ == '__main__':
    unittest.main()
