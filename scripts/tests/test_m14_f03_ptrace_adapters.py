"""Link the actual opt-in ptrace adapters to typed C observation providers.

Provider declarations and callback typedefs come from the real project sources.
The providers only observe arguments/results: this is mixed-language ABI/source
coverage, not a production provider link, thread-lifetime or native qualification.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def declaration(source, name):
    matches = re.findall(
        r"^(?:extern\s+)?(?:unsigned long|int)\s+" + name + r"\([^;{}]*\);",
        source, re.M)
    if len(matches) != 1:
        raise ValueError(f"Expected one genuine declaration for {name}")
    return matches[0]


class PtraceAdaptersTests(unittest.TestCase):
    def test_actual_c_and_rust_callbacks_against_c_provider_signatures(self):
        cc = os.environ.get("CC") or shutil.which("gcc")
        rustc = os.environ.get("RUSTC") or shutil.which("rustc")
        if cc is None or rustc is None:
            self.skipTest("C and Rust compilers required")
        generic = (ROOT / "kernel/syscall.c").read_text()
        header = (ROOT / "kernel/include/process.h").read_text()
        start = generic.index("#ifdef MCKERNEL_RUST_F03_FORWARD_ADAPTERS\n"
                              "extern long ptrace_detach_do_kill_bridge")
        end_marker = "#endif /* MCKERNEL_RUST_F03_FORWARD_ADAPTERS */"
        end = generic.index(end_marker, start) + len(end_marker)
        guards = generic[start:end]
        typedefs = []
        for name in ("ptrace_do_kill_thread_fn_t", "ptrace_wakeup_thread_fn_t"):
            match = re.search(r"typedef\s+[^;]*\(\*" + name + r"\)[^;]*;", generic)
            self.assertIsNotNone(match)
            typedefs.append(match.group(0))
        harness = r'''
#include <stddef.h>
#include <limits.h>
struct thread;
struct siginfo;
@DECLARATIONS@
@TYPEDEFS@
@GUARDS@
_Static_assert(__builtin_types_compatible_p(
    __typeof__(&ptrace_detach_do_kill_bridge), ptrace_do_kill_thread_fn_t),
    "ptrace kill callback signature");
_Static_assert(__builtin_types_compatible_p(
    __typeof__(&ptrace_detach_wakeup_bridge), ptrace_wakeup_thread_fn_t),
    "ptrace wake callback signature");
static void *want_thread;
static const void *want_info;
static int want_pid, want_tid, want_sig, want_cont, want_states;
static int bad, kills, wakes, wake_result;
static unsigned long kill_result;
unsigned long do_kill(struct thread *thread, int pid, int tid, int sig,
                      struct siginfo *info, int ptracecont)
{
    ++kills;
    if (thread != want_thread || info != want_info || pid != want_pid ||
        tid != want_tid || sig != want_sig || ptracecont != want_cont)
        bad = 1;
    return kill_result;
}
int sched_wakeup_thread(struct thread *thread, int valid_states)
{
    ++wakes;
    if (thread != want_thread || valid_states != want_states) bad = 1;
    return wake_result;
}
int main(void)
{
    long thread_storage, info_storage;
    void *threads[] = {NULL, &thread_storage};
    const void *infos[] = {NULL, &info_storage};
    const int values[] = {INT_MIN, -1, 0, INT_MAX};
    const unsigned long results[] = {0, 1, 0x180000001UL,
                                    (unsigned long)LONG_MIN,
                                    (unsigned long)-4095L, ULONG_MAX};
    ptrace_do_kill_thread_fn_t kill_callback = ptrace_detach_do_kill_bridge;
    ptrace_wakeup_thread_fn_t wake_callback = ptrace_detach_wakeup_bridge;
    for (unsigned int t = 0; t < 2; ++t)
    for (unsigned int i = 0; i < 2; ++i)
    for (unsigned int v = 0; v < 4; ++v)
    for (unsigned int r = 0; r < 6; ++r) {
        want_thread = threads[t]; want_info = infos[i];
        want_pid = values[v]; want_tid = values[(v + 1) % 4];
        want_sig = values[(v + 2) % 4]; want_cont = values[(v + 3) % 4];
        kill_result = results[r];
        bad = kills = wakes = 0;
        long got = kill_callback(want_thread, want_pid, want_tid, want_sig,
                                 want_info, want_cont);
        if ((unsigned long)got != kill_result || bad || kills != 1 || wakes != 0)
            return 1;
    }
    for (unsigned int t = 0; t < 2; ++t)
    for (unsigned int v = 0; v < 4; ++v)
    for (unsigned int r = 0; r < 4; ++r) {
        want_thread = threads[t]; want_states = values[v];
        wake_result = values[r];
        bad = kills = wakes = 0;
        wake_callback(want_thread, want_states);
        if (bad || kills != 0 || wakes != 1) return 2;
    }
    return 0;
}
'''.replace("@DECLARATIONS@", "\n".join(
            declaration(header, name) for name in ("do_kill", "sched_wakeup_thread")))
        harness = harness.replace("@TYPEDEFS@", "\n".join(typedefs)).replace("@GUARDS@", guards)
        rust = ('#![no_std]\n'
                f'#[path = "{ROOT / "kernel/rust/abi.rs"}"] mod abi;\n'
                f'#[path = "{ROOT / "kernel/rust/f03_ptrace_adapters.rs"}"] mod adapters;\n')
        with tempfile.TemporaryDirectory(prefix="m14-ptrace-adapters-") as directory:
            path = Path(directory)
            csource, rsource = path / "fixture.c", path / "fixture.rs"
            csource.write_text(harness)
            rsource.write_text(rust)
            obj = path / "adapters.o"
            result = subprocess.run([
                rustc, "--edition=2021", "--crate-type=lib", "-C", "panic=abort",
                "--emit=obj", "-o", str(obj), str(rsource),
            ], capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for selected in (False, True):
                with self.subTest(rust_selected=selected):
                    binary = path / ("rust-callbacks" if selected else "c-callbacks")
                    command = [cc, "-std=gnu11", "-Werror=incompatible-pointer-types",
                               "-fsanitize=undefined", "-fno-sanitize-recover=all",
                               str(csource), "-o", str(binary)]
                    if selected:
                        command.extend(["-DMCKERNEL_RUST_F03_FORWARD_ADAPTERS=1", str(obj)])
                    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
